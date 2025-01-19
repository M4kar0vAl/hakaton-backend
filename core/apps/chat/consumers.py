from typing import Type, Tuple

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db.models import QuerySet, Prefetch, Q, OuterRef, Subquery, Max, F
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.serializers import Serializer
from rest_framework.utils.serializer_helpers import ReturnList

from core.apps.brand.models import Brand
from core.apps.chat.mixins import ConsumerSerializationMixin, ConsumerUtilitiesMixin, ConsumerPaginationMixin
from core.apps.chat.models import Room, Message
from core.apps.chat.permissions import (
    IsAuthenticatedConnect,
    IsAdminUser,
    IsBrand,
    CanUserJoinRoom,
    UserInRoom,
    CanCreateMessage,
    CanAdminAct, CanAdminJoinRoom
)
from core.apps.chat.serializers import RoomSerializer, MessageSerializer, RoomListSerializer
from core.apps.chat.utils import reply_to_groups

User = get_user_model()


class RoomConsumer(
    GenericAsyncAPIConsumer,
    ConsumerSerializationMixin,
    ConsumerUtilitiesMixin,
    ConsumerPaginationMixin
):
    serializer_class = RoomSerializer
    lookup_field = "pk"
    permission_classes = [IsAuthenticatedConnect, IsBrand]

    async def get_permissions(self, action: str, **kwargs):
        permission_instances = await super().get_permissions(action, **kwargs)

        if action == 'join_room':
            permission_instances += [CanUserJoinRoom()]
        elif action in (
                'leave_room',
                'get_room_messages',
                'edit_message',
                'delete_messages',
        ):
            permission_instances += [UserInRoom()]
        elif action == 'create_message':
            permission_instances += [CanCreateMessage()]

        return permission_instances

    def get_queryset(self, **kwargs) -> QuerySet:
        if 'action' in kwargs:
            action_ = kwargs['action']
            if action_ == 'get_room_messages':
                return self.room.messages.order_by('-created_at', 'id')
            elif action_ == 'get_rooms':
                last_message_in_room = Message.objects.filter(
                    pk=Subquery(Message.objects.filter(room=OuterRef('room')).order_by('-created_at').values('pk')[:1])
                )

                return self.scope['user'].rooms.prefetch_related(
                    Prefetch(
                        'participants',
                        queryset=User.objects.filter(~Q(pk=self.scope['user'].id)).select_related('brand__category'),
                        to_attr='interlocutor_users'
                    ),
                    Prefetch(
                        'messages',
                        queryset=last_message_in_room,
                        to_attr='last_message'
                    )
                ).annotate(
                    last_message_created_at=Max('messages__created_at')
                ).order_by(
                    F('last_message_created_at').desc(nulls_last=True)
                )

        return self.scope['user'].rooms.all()

    def get_serializer_class(self, **kwargs) -> Type[Serializer]:
        if kwargs['action'] in ('create_message', 'get_room_messages'):
            return MessageSerializer
        elif kwargs['action'] == 'get_rooms':
            return RoomListSerializer
        return super().get_serializer_class()

    async def connect(self):
        self.user_group_name = f'user_{self.scope["user"].pk}'
        self.brand = await self.get_brand()
        self.brand_rooms = await self.get_brand_rooms_pk_set()
        self.action_paginators = {}

        await self.add_group(self.user_group_name)

        if 'chat' in self.scope['subprotocols']:
            await self.accept('chat')
        else:
            await self.close()

    async def disconnect(self, code):
        if hasattr(self, 'user_group_name'):
            await self.remove_group(self.user_group_name)

        self.delete_all_paginators()

    @action()
    async def get_rooms(self, page: int, **kwargs) -> Tuple[ReturnList, int]:
        action_ = kwargs.get('action')
        queryset = await database_sync_to_async(self.get_queryset)(**kwargs)

        paginator = await self.paginate_queryset(queryset, 100, action_)

        page_objs = await self.get_page_objects(paginator, page)

        rooms_data = await self.get_serialized_data(page_objs, many=True, **kwargs)

        data = await self.get_paginated_data(rooms_data, paginator, page)

        return data, status.HTTP_200_OK

    @action()
    async def join_room(self, room_pk, **kwargs):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        self.room = await database_sync_to_async(self.get_object)(pk=room_pk)
        self.room_group_name = f'room_{room_pk}'

        await self.add_group(self.room_group_name)

        room_data = await self.get_serialized_data(self.room, **kwargs)

        return room_data, status.HTTP_200_OK

    @action()
    async def leave_room(self, **kwargs):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)
            delattr(self, 'room_group_name')

        self.delete_paginator_for_action('get_room_messages')

        pk = self.room.pk
        delattr(self, 'room')

        return {'response': f'Leaved room {pk} successfully!'}, status.HTTP_200_OK

    @action()
    async def get_room_messages(self, page: int, **kwargs):
        action_ = kwargs.get('action')
        messages = await database_sync_to_async(self.get_queryset)(**kwargs)

        paginator = await self.paginate_queryset(messages, 100, action_)

        page_objs = await self.get_page_objects(paginator, page)

        messages_data = await self.get_serialized_data(page_objs, many=True, **kwargs)

        data = await self.get_paginated_data(messages_data, paginator, page)

        return data, status.HTTP_200_OK

    @action()
    async def create_message(self, msg_text: str, **kwargs):
        message = await Message.objects.acreate(
            room=self.room,
            user=self.scope['user'],
            text=msg_text
        )

        message_data = await self.get_serialized_data(message, **kwargs)

        await reply_to_groups(
            groups=(self.room_group_name,),
            handler_name='data_to_groups',
            action=kwargs['action'],
            data=message_data,
            status=status.HTTP_201_CREATED,
            request_id=kwargs['request_id']
        )

    @action()
    async def edit_message(self, msg_id, edited_msg_text, **kwargs):
        updated = bool(await self.edit_message_in_db(msg_id, edited_msg_text))

        if updated:
            data = {
                'room_id': self.room.pk,
                'message_id': msg_id,
                'message_text': edited_msg_text,
            }
            await reply_to_groups(
                groups=(self.room_group_name,),
                handler_name='data_to_groups',
                action=kwargs['action'],
                data=data,
                status=status.HTTP_200_OK,
                request_id=kwargs['request_id']
            )
        else:
            raise NotFound(
                f"Message with id: {msg_id} and user: {self.scope['user'].email} not found! "
                "Check whether the user is the author of the message and the id is correct!"
            )

    @action()
    async def delete_messages(self, msg_id_list: list[int], **kwargs):
        # get existing messages ids
        existing = Message.objects.filter(pk__in=msg_id_list, user=self.scope['user'], room=self.room).values_list(
            'pk',
            flat=True
        )

        # calculate not existing ids
        not_existing = await database_sync_to_async(set)(msg_id_list) - await database_sync_to_async(set)(existing)

        # delete nothing and raise exception if there are not existing messages
        if not_existing:
            raise NotFound(f'Messages with ids {list(not_existing)} do not exist! Nothing was deleted.')

        # if all messages were found then delete them
        await self.delete_messages_in_db(msg_id_list)

        data = {
            'room_id': self.room.pk,
            'messages_ids': msg_id_list,
        }

        errors = []

        await reply_to_groups(
            groups=(self.room_group_name,),
            handler_name='data_to_groups',
            action=kwargs['action'],
            data=data,
            errors=errors,
            status=status.HTTP_200_OK,
            request_id=kwargs['request_id']
        )

    @action()
    async def get_support_room(self, **kwargs):
        room, created = await self.get_or_create_support_room()

        room_data = await self.get_serialized_data(room, **kwargs)

        if created:
            return room_data, status.HTTP_201_CREATED

        return room_data, status.HTTP_200_OK

    async def data_to_groups(self, event):
        await self.send_json(event['payload'])

    @database_sync_to_async
    def get_brand(self) -> Brand:
        return self.scope['user'].brand

    @database_sync_to_async
    def get_brand_rooms_pk_set(self):
        return set(self.scope['user'].rooms.values_list('pk', flat=True))


class AdminRoomConsumer(
    GenericAsyncAPIConsumer,
    ConsumerSerializationMixin,
    ConsumerUtilitiesMixin,
    ConsumerPaginationMixin
):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = 'pk'
    permission_classes = [IsAdminUser]

    async def get_permissions(self, action: str, **kwargs):
        permission_instances = await super().get_permissions(action, **kwargs)

        if action == 'join_room':
            permission_instances += [CanAdminJoinRoom()]
        elif action in (
                'leave_room',
                'get_room_messages',
        ):
            permission_instances += [UserInRoom()]
        elif action in (
                'create_message',
                'edit_message',
                'delete_messages',
        ):
            permission_instances += [CanAdminAct()]

        return permission_instances

    def get_queryset(self, **kwargs) -> QuerySet:
        if 'action' in kwargs:
            action_ = kwargs['action']
            if action_ == 'get_room_messages':
                return self.room.messages.order_by('-created_at', 'id')
            elif action_ == 'get_rooms':
                last_message_in_room = Message.objects.filter(
                    pk=Subquery(Message.objects.filter(room=OuterRef('room')).order_by('-created_at').values('pk')[:1])
                )

                return Room.objects.prefetch_related(
                    Prefetch(
                        'participants',
                        queryset=User.objects.filter(~Q(pk=self.scope['user'].id)).select_related('brand__category'),
                        to_attr='interlocutor_users'
                    ),
                    Prefetch(
                        'messages',
                        queryset=last_message_in_room,
                        to_attr='last_message'
                    )
                ).annotate(
                    last_message_created_at=Max('messages__created_at')
                ).order_by(
                    F('last_message_created_at').desc(nulls_last=True)
                )

        return super().get_queryset(**kwargs)

    def get_serializer_class(self, **kwargs) -> Type[Serializer]:
        if kwargs['action'] in ('create_message', 'get_room_messages'):
            return MessageSerializer
        elif kwargs['action'] == 'get_rooms':
            return RoomListSerializer

        return super().get_serializer_class()

    async def connect(self):
        self.action_paginators = {}

        if 'admin-chat' in self.scope['subprotocols']:
            await self.accept('admin-chat')
        else:
            await self.close()

    async def disconnect(self, code):
        self.delete_all_paginators()

    @action()
    async def get_rooms(self, page: int, **kwargs) -> Tuple[ReturnList, int]:
        action_ = kwargs.get('action')
        queryset = await database_sync_to_async(self.get_queryset)(**kwargs)

        paginator = await self.paginate_queryset(queryset, 100, action_)

        page_objs = await self.get_page_objects(paginator, page)

        rooms_data = await self.get_serialized_data(page_objs, many=True, **kwargs)

        data = await self.get_paginated_data(rooms_data, paginator, page)

        return data, status.HTTP_200_OK

    @action()
    async def join_room(self, room_pk, **kwargs):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        self.room = await database_sync_to_async(self.get_object)(pk=room_pk)
        self.room_group_name = f'room_{room_pk}'

        # can create/edit/delete messages only in support chat
        # can view messages in all chats
        self.can_message = self.room.type == Room.SUPPORT

        await self.add_group(self.room_group_name)

        room_data = await self.get_serialized_data(self.room, **kwargs)

        return room_data, status.HTTP_200_OK

    @action()
    async def leave_room(self, **kwargs):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        self.delete_paginator_for_action('get_room_messages')

        pk = self.room.pk
        delattr(self, 'room')
        delattr(self, 'can_message')

        return {'response': f'Leaved room {pk} successfully!'}, status.HTTP_200_OK

    @action()
    async def get_room_messages(self, page: int, **kwargs):
        action_ = kwargs.get('action')
        messages = await database_sync_to_async(self.get_queryset)(**kwargs)

        paginator = await self.paginate_queryset(messages, 100, action_)

        page_objs = await self.get_page_objects(paginator, page)

        messages_data = await self.get_serialized_data(page_objs, many=True, **kwargs)

        data = await self.get_paginated_data(messages_data, paginator, page)

        return data, status.HTTP_200_OK

    @action()
    async def create_message(self, msg_text, **kwargs):
        message = await Message.objects.acreate(
            room=self.room,
            user=self.scope['user'],
            text=msg_text
        )

        message_data = await self.get_serialized_data(message, **kwargs)

        await reply_to_groups(
            groups=(self.room_group_name,),
            handler_name='data_to_groups',
            action=kwargs['action'],
            data=message_data,
            status=status.HTTP_201_CREATED,
            request_id=kwargs['request_id']
        )

    @action()
    async def edit_message(self, msg_id, edited_msg_text, **kwargs):
        updated = bool(await self.edit_message_in_db(msg_id, edited_msg_text))

        if updated:
            data = {
                'room_id': self.room.pk,
                'message_id': msg_id,
                'message_text': edited_msg_text,
            }
            await reply_to_groups(
                groups=(self.room_group_name,),
                handler_name='data_to_groups',
                action=kwargs['action'],
                data=data,
                status=status.HTTP_200_OK,
                request_id=kwargs['request_id']
            )
        else:
            raise NotFound(
                f"Message with id: {msg_id} and user: {self.scope['user'].email} not found! "
                "Check whether the user is the author of the message and the id is correct! "
            )

    @action()
    async def delete_messages(self, msg_id_list: list[int], **kwargs):
        # get existing messages ids
        existing = Message.objects.filter(pk__in=msg_id_list, user=self.scope['user'], room=self.room).values_list(
            'pk',
            flat=True
        )

        # calculate not existing ids
        not_existing = await database_sync_to_async(set)(msg_id_list) - await database_sync_to_async(set)(existing)

        # delete nothing and raise exception if there are not existing messages
        if not_existing:
            raise NotFound(f'Messages with ids {list(not_existing)} do not exist! Nothing was deleted.')

        await self.delete_messages_in_db(msg_id_list)

        data = {
            'room_id': self.room.pk,
            'messages_ids': msg_id_list,
        }

        errors = []

        await reply_to_groups(
            groups=(self.room_group_name,),
            handler_name='data_to_groups',
            action=kwargs['action'],
            data=data,
            errors=errors,
            status=status.HTTP_200_OK,
            request_id=kwargs['request_id']
        )

    @action()
    async def get_support_room(self, **kwargs):
        room, created = await self.get_or_create_support_room()

        room_data = await self.get_serialized_data(room, **kwargs)

        if created:
            return room_data, status.HTTP_201_CREATED

        return room_data, status.HTTP_200_OK

    async def data_to_groups(self, event):
        await self.send_json(event['payload'])
