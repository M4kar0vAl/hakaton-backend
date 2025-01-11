from typing import Type, Optional

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, InvalidPage
from django.db import transaction, DatabaseError
from django.db.models import QuerySet, Prefetch, Q, OuterRef, Subquery
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.mixins import ListModelMixin
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.serializers import Serializer

from core.apps.brand.models import Brand, Match
from core.apps.chat.exceptions import BadRequest, ServerError
from core.apps.chat.models import Room, Message
from core.apps.chat.permissions import IsAuthenticatedConnect, IsAdminUser, IsBrand
from core.apps.chat.serializers import RoomSerializer, MessageSerializer, RoomListSerializer
from core.apps.chat.utils import reply_to_groups

User = get_user_model()


class RoomConsumer(ListModelMixin,
                   GenericAsyncAPIConsumer):
    serializer_class = RoomSerializer
    lookup_field = "pk"
    permission_classes = [IsAuthenticatedConnect, IsBrand]

    def get_queryset(self, **kwargs) -> QuerySet:
        if 'action' in kwargs:
            action_ = kwargs['action']
            if action_ == 'get_room_messages':
                return self.room.messages.order_by('-created_at', 'id')
            elif action_ == 'list':
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
                )

        return self.scope['user'].rooms.all()

    def get_serializer_class(self, **kwargs) -> Type[Serializer]:
        if kwargs['action'] in ('create_message', 'get_room_messages'):
            return MessageSerializer
        elif kwargs['action'] == 'list':
            return RoomListSerializer
        return super().get_serializer_class()

    async def connect(self):
        self.user_group_name = f'user_{self.scope["user"].pk}'
        self.brand = await self.get_brand()
        self.brand_rooms = await self.get_brand_rooms_pk_set()

        await self.add_group(self.user_group_name)

        if 'chat' in self.scope['subprotocols']:
            await self.accept('chat')
        else:
            await self.close()

    async def disconnect(self, code):
        if hasattr(self, 'user_group_name'):
            await self.remove_group(self.user_group_name)

        if hasattr(self, 'paginator'):
            delattr(self, 'paginator')

    @action()
    async def join_room(self, room_pk, **kwargs):
        if hasattr(self, 'room') and self.room.pk == room_pk:
            raise BadRequest('You have already joined this room!')

        if room_pk not in self.brand_rooms:
            # update related room_pks
            self.brand_rooms = await self.get_brand_rooms_pk_set()

            # check again
            if room_pk not in self.brand_rooms:
                raise PermissionDenied('You cannot enter a room you are not a member of')

        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        self.room = await database_sync_to_async(self.get_object)(pk=room_pk)
        self.room_group_name = f'room_{room_pk}'

        await self.add_group(self.room_group_name)

        room_data = await self.get_serialized_room(**kwargs)

        return room_data, status.HTTP_200_OK

    @action()
    async def leave_room(self, **kwargs):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        if hasattr(self, 'paginator'):
            delattr(self, 'paginator')

        if hasattr(self, 'room'):
            pk = self.room.pk
            delattr(self, 'room')
            return {'response': f'Leaved room {pk} successfully!'}, status.HTTP_200_OK

        raise BadRequest("Action 'leave_room' not allowed. You are not in the room")

    @action()
    async def get_room_messages(self, page: int, **kwargs):
        await self.check_user_in_room()

        messages = await database_sync_to_async(self.get_queryset)(**kwargs)

        if not hasattr(self, 'paginator'):
            self.paginator = Paginator(messages, 100)

        await self.check_page_number(page)

        page = await database_sync_to_async(self.paginator.get_page)(page)

        try:
            next_ = page.next_page_number()
        except InvalidPage:
            next_ = None

        page_objs = page.object_list

        messages_data = await self.get_serialized_message(page_objs, many=True, **kwargs)

        data = {
            'messages': messages_data,
            'next': next_
        }

        return data, status.HTTP_200_OK

    @action()
    async def create_message(self, msg_text: str, **kwargs):
        await self.check_user_can_create_message()

        message = await database_sync_to_async(Message.objects.create)(
            room=self.room,
            user=self.scope['user'],
            text=msg_text
        )

        message_data = await self.get_serialized_message(message, **kwargs)

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
        await self.check_user_in_room()

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
        await self.check_user_in_room()

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

        room_data = await self.get_serialized_room(room=room, **kwargs)

        if created:
            return room_data, status.HTTP_201_CREATED
        else:
            return room_data, status.HTTP_200_OK

    async def data_to_groups(self, event):
        await self.send_json(event['payload'])

    async def check_user_in_room(self):
        """
        Check whether the user connected to any room or not.
        If not raises exception BadRequest, otherwise does nothing.
        """
        if not hasattr(self, 'room'):
            raise BadRequest("Action not allowed. You are not in the room!")

    async def check_user_can_create_message(self):
        """
        Check whether the current user allowed to create a message in room.

        At first check if the user in the room
        After that, if room type is instant and this user has already sent message, then raises BadRequest
        """
        await self.check_user_in_room()

        if self.room.type == Room.INSTANT:
            match = await Match.objects.aget(room=self.room)
            if match.initiator_id != self.brand.id:
                # if the user is not the initiator of the instant coop
                raise BadRequest(
                    "You cannot send a message to this room. "
                    "Like this brand in response to be able to send a message."
                )
            elif await self.scope['user'].messages.filter(room=self.room).aexists():
                # if user has already sent message to this instant room
                raise BadRequest("Action not allowed. You have already sent message to this user.")

    @database_sync_to_async
    def check_page_number(self, page) -> None:
        if type(page) is not int:
            raise BadRequest('Page number must be an integer!')

        if page not in self.paginator.page_range:
            raise BadRequest(f'Page {page} does not exist!')

    @database_sync_to_async
    def get_brand(self) -> Brand:
        return self.scope['user'].brand

    @database_sync_to_async
    def get_brand_rooms_pk_set(self):
        return set(self.scope['user'].rooms.values_list('pk', flat=True))

    @database_sync_to_async
    def edit_message_in_db(self, msg_id: int, text: str) -> int:
        """
        Edit message text in db. Allows editing only messages authored by the current user.

        Args:
            msg_id: primary key of message being edited
            text: new text to be set

        Returns number of rows matched in db.
        Either 0 if message with msg_id was not found in db
        or 1 if message was found and updated
        """
        # filter uses user = self.scope['user'] to allow editing current user's messages only
        # if message with id msg_id don't belong to user, then nothing happens
        return Message.objects.filter(pk=msg_id, user=self.scope['user'], room=self.room).update(text=text)

    @database_sync_to_async
    def delete_messages_in_db(self, msg_id_list: list[int]) -> int:
        """
        Delete messages from db. Allows deleting only messages authored by the current user.

        Args:
            msg_id_list: list of ids of message to delete

        Returns number of messages deleted
        """
        return Message.objects.filter(pk__in=msg_id_list, user=self.scope['user'], room=self.room).delete()[0]

    @database_sync_to_async
    def get_or_create_support_room(self) -> tuple[Room, bool]:
        """
        Get support room for current brand. If room does not exist, then create it.

        Returns room instance and status whether it was created or not.
        """
        created = False  # whether a new room was created
        try:
            room = self.scope['user'].rooms.get(type=Room.SUPPORT)
        except Room.DoesNotExist:
            try:
                with transaction.atomic():
                    room = Room.objects.create(type=Room.SUPPORT)
                    room.participants.add(self.scope['user'])
                    created = True
            except DatabaseError:
                raise ServerError("Room creation failed! Please try again.")

        return room, created

    @database_sync_to_async
    def get_serialized_room(self, room: Optional[Room] = None, **kwargs):
        """
        Get serialized room data.
        If room argument is passed, then serializes that room, otherwise serializes current room.

        Returns serializer data.

        Args:
            room: room instance to be serialized [optional]
            kwargs: keyword arguments from action
        """
        if room is None:
            serializer = self.get_serializer(action_kwargs=kwargs, instance=self.room)
        else:
            serializer = self.get_serializer(action_kwargs=kwargs, instance=room)
        return serializer.data

    @database_sync_to_async
    def get_serialized_message(self, message: Message | QuerySet[Message], many: bool = False, **kwargs):
        """
        Serializes messages and returns serializer data.

        Args:
            message: Message model instance or queryset of model instances to be serialized
            many: flag that indicates whether to serialize one message or queryset
        """
        serializer = self.get_serializer(action_kwargs=kwargs, instance=message, many=many)
        return serializer.data


class AdminRoomConsumer(ListModelMixin,
                        GenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = 'pk'
    permission_classes = [IsAdminUser]

    def get_queryset(self, **kwargs) -> QuerySet:
        if 'action' in kwargs:
            if kwargs['action'] == 'get_room_messages':
                return self.room.messages
        return super().get_queryset(**kwargs)

    def get_serializer_class(self, **kwargs) -> Type[Serializer]:
        if kwargs['action'] in ('create_message', 'get_room_messages'):
            return MessageSerializer

        return super().get_serializer_class()

    async def connect(self):
        self.brand = await self.get_brand()

        if 'admin-chat' in self.scope['subprotocols']:
            await self.accept('admin-chat')
        else:
            await self.close()

    @action()
    async def join_room(self, room_pk, **kwargs):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        self.room = await database_sync_to_async(self.get_object)(pk=room_pk)
        self.room_group_name = f'room_{room_pk}'

        # can create/edit/delete messages only in support chat or in default after-match chat (if admin has brand)
        # can view messages in all chats
        self.can_message = self.room.type in [Room.SUPPORT, Room.HELP] or await self.is_user_in_participants()

        await self.add_group(self.room_group_name)

        room_data = await self.get_serialized_room(**kwargs)

        return room_data, status.HTTP_200_OK

    @action()
    async def leave_room(self, **kwargs):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        if hasattr(self, 'room'):
            pk = self.room.pk
            delattr(self, 'room')
            delattr(self, 'can_message')
            return {'response': f'Leaved room {pk} successfully!'}, status.HTTP_200_OK
        raise BadRequest("Action 'leave_room' not allowed. You are not in the room")

    @action()
    async def get_room_messages(self, **kwargs):
        if not hasattr(self, 'room'):
            raise BadRequest("Action not allowed. You are not in the room!")

        messages = await database_sync_to_async(self.get_queryset)(**kwargs)
        messages_data = await self.get_serialized_message(messages, many=True, **kwargs)

        return messages_data, status.HTTP_200_OK

    @action()
    async def create_message(self, msg_text, **kwargs):
        await self.check_admin_can_act()

        message = await database_sync_to_async(Message.objects.create)(
            room=self.room,
            user=self.scope['user'],
            text=msg_text
        )

        message_data = await self.get_serialized_message(message, **kwargs)

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
        await self.check_admin_can_act()

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
                "Check if messages belong to the current user's room!"
            )

    @action()
    async def delete_messages(self, msg_id_list: list[int], **kwargs):
        await self.check_admin_can_act()

        deleted_count = await self.delete_messages_in_db(msg_id_list)

        if deleted_count == 0:
            raise NotFound(
                f"Messages with ids: {msg_id_list} were not found! Nothing was deleted! "
                "Check whether the user is the author of the message and the ids are correct! "
                "Check if messages belong to the current user's room!"
            )

        data = {
            'room_id': self.room.pk,
            'messages_ids': msg_id_list,
        }

        errors = []

        if deleted_count != len(msg_id_list):
            errors.append(
                "Not all of the requested messages were deleted! "
                "Check whether the user is the author of the message and the ids are correct! "
                "Check if messages belong to the current user's room!"
            )

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

        room_data = await self.get_serialized_room(room=room, **kwargs)

        if created:
            return room_data, status.HTTP_201_CREATED
        else:
            return room_data, status.HTTP_200_OK

    async def data_to_groups(self, event):
        await self.send_json(event['payload'])

    async def check_admin_can_act(self):
        """
        Check whether admin can create, edit and delete messages in room.

        If admin not connected to a room, then raises BadRequest exception.
        If room is not support or help room, then raises PermissionDenied exception.
        Otherwise, does nothing.
        """
        try:
            if not self.can_message:
                raise PermissionDenied(
                    "Action not allowed. "
                    f"You cannot write to room of type [{self.room.get_type_display()}] "
                    "if you are not a participant of it!"
                )
        except AttributeError:
            raise BadRequest("Action not allowed. You are not in the room!")

    @database_sync_to_async
    def get_brand(self) -> Brand | None:
        try:
            return self.scope['user'].brand
        except User.brand.RelatedObjectDoesNotExist:
            return None

    @database_sync_to_async
    def is_user_in_participants(self):
        return self.scope['user'] in self.room.participants.all()

    @database_sync_to_async
    def edit_message_in_db(self, msg_id: int, text: str) -> int:
        """
        Edit message text in db. Allows editing only messages authored by the current user.
        Admins are not exception.

        Args:
            msg_id: primary key of message being edited
            text: new text to be set

        Returns number of rows matched in db.
        Either 0 if message with msg_id was not found in db
        or 1 if message was found and updated
        """
        # filter uses user = self.scope['user'] to allow editing current user's messages only
        # if message with id msg_id don't belong to user, then nothing happens
        return Message.objects.filter(pk=msg_id, user=self.scope['user'], room=self.room).update(text=text)

    @database_sync_to_async
    def delete_messages_in_db(self, msg_id_list: list[int]) -> int:
        """
        Delete messages from db. Can only delete own messages in current room.

        Args:
            msg_id_list: list of ids of message to delete

        Returns number of messages deleted
        """
        return Message.objects.filter(pk__in=msg_id_list, user=self.scope['user'], room=self.room).delete()[0]

    @database_sync_to_async
    def get_or_create_support_room(self) -> tuple[Room, bool]:
        """
        Get support room for current user. If room does not exist, then create it.

        Returns room instance and status whether it was created or not.
        """
        created = False  # whether a new room was created
        try:
            room = self.scope['user'].rooms.get(type=Room.SUPPORT)
        except Room.MultipleObjectsReturned:
            raise ServerError('Multiple rooms returned! Must be exactly one.')
        except Room.DoesNotExist:
            try:
                with transaction.atomic():
                    room = Room.objects.create(type=Room.SUPPORT)
                    room.participants.add(self.scope['user'])
                    created = True
            except DatabaseError:
                raise ServerError('Room creation failed! Please try again.')

        return room, created

    @database_sync_to_async
    def get_serialized_room(self, room: Optional[Room] = None, **kwargs):
        """
        Get serialized room data.
        If room argument is passed, then serializes that room, otherwise serializes current room.

        Returns serializer data.

        Args:
            room: room instance to be serialized [optional]
            kwargs: keyword arguments from action
        """
        if room is None:
            serializer = self.get_serializer(action_kwargs=kwargs, instance=self.room)
        else:
            serializer = self.get_serializer(action_kwargs=kwargs, instance=room)
        return serializer.data

    @database_sync_to_async
    def get_serialized_message(self, message: Message | QuerySet[Message], many: bool = False, **kwargs):
        """
        Serializes messages and returns serializer data.

        Args:
            message: Message model instance or queryset of model instances to be serialized
            many: flag that indicates whether to serialize one message or queryset
        """
        serializer = self.get_serializer(action_kwargs=kwargs, instance=message, many=many)
        return serializer.data
