from typing import Type

from channels.db import database_sync_to_async
from django.db.models import QuerySet
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.mixins import ListModelMixin
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.serializers import Serializer

from core.apps.brand.models import Brand
from core.apps.chat.exceptions import BadRequest
from core.apps.chat.models import Room, Message
from core.apps.chat.permissions import IsAuthenticatedConnect, IsAdminUser
from core.apps.chat.serializers import RoomSerializer, MessageSerializer
from core.apps.chat.utils import reply_to_groups, get_method_name


class RoomConsumer(ListModelMixin,
                   GenericAsyncAPIConsumer):
    serializer_class = RoomSerializer
    lookup_field = "pk"
    permission_classes = [IsAuthenticatedConnect]

    def get_queryset(self, **kwargs) -> QuerySet:
        return self.brand.rooms.all()

    def get_serializer_class(self, **kwargs) -> Type[Serializer]:
        if kwargs['action'] == 'create_message':
            return MessageSerializer
        return super().get_serializer_class()

    async def connect(self):
        self.user_group_name = f'user_{self.scope["user"].pk}'
        self.brand = await self.get_brand()
        self.brand_rooms = await self.get_brand_rooms_pk_set()

        await self.add_group(self.user_group_name)

        await self.accept()

    async def disconnect(self, code):
        await self.remove_group(self.user_group_name)

    @action()
    async def join_room(self, room_pk, **kwargs):
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

        if hasattr(self, 'room'):
            pk = self.room.pk
            delattr(self, 'room')
            return {'response': f'Leaved room {pk} successfully!'}, status.HTTP_200_OK

        raise BadRequest("Action 'leave_room' not allowed. You are not in the room")

    @action()
    async def create_message(self, msg_text: str, **kwargs):
        await self.check_user_in_room()

        message = await database_sync_to_async(Message.objects.create)(
            room=self.room,
            user=self.scope['user'],
            text=msg_text
        )

        message_data = await self.get_serialized_message(message, **kwargs)

        await reply_to_groups(
            groups=(self.room_group_name,),
            handler_name='data_to_groups',
            action=get_method_name(),
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
                action=get_method_name(),
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

        deleted_count = await self.delete_messages_in_db(msg_id_list)

        if deleted_count == 0:
            raise NotFound(f"Messages with ids: {msg_id_list} were not found! Nothing was deleted!")

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
            action=get_method_name(),
            data=data,
            errors=errors,
            status=status.HTTP_200_OK,
            request_id=kwargs['request_id']
        )

    @action()
    async def current_room_info(self, **kwargs):
        await self.check_user_in_room()

        room_data = await self.get_serialized_room(**kwargs)

        await reply_to_groups(
            groups=(self.user_group_name,),
            handler_name='data_to_groups',
            action=get_method_name(),
            data=room_data,
            status=status.HTTP_200_OK,
            request_id=kwargs['request_id']
        )

    async def data_to_groups(self, event):
        await self.send_json(event['payload'])

    async def check_user_in_room(self):
        """
        Check whether the user connected to any room or not.
        If not raises exception BadRequest, otherwise does nothing.
        """
        if not hasattr(self, 'room'):
            raise BadRequest("Action not allowed. You are not in the room!")

    @database_sync_to_async
    def get_brand(self) -> Brand:
        return Brand.objects.get(user=self.scope['user'])

    @database_sync_to_async
    def get_brand_rooms_pk_set(self):
        return set(self.brand.rooms.values_list('pk', flat=True))

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
        return Message.objects.filter(pk=msg_id, user=self.scope['user']).update(text=text)

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
    def get_serialized_room(self, **kwargs):
        serializer = self.get_serializer(action_kwargs=kwargs, instance=self.room)
        return serializer.data

    @database_sync_to_async
    def get_serialized_message(self, message, **kwargs):
        serializer = self.get_serializer(action_kwargs=kwargs, instance=message)
        return serializer.data


class AdminRoomConsumer(ListModelMixin,
                        GenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = 'pk'
    permission_classes = [IsAdminUser]

    def get_serializer_class(self, **kwargs) -> Type[Serializer]:
        if kwargs['action'] == 'create_message':
            return MessageSerializer

        return super().get_serializer_class()

    @action()
    async def join_room(self, room_pk, **kwargs):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        self.room = await database_sync_to_async(self.get_object)(pk=room_pk)
        self.room_group_name = f'room_{room_pk}'

        # check if there is business subscription brand
        self.can_message = self.room.has_business

        await self.add_group(self.room_group_name)

        room_data = await self.get_serialized_room(**kwargs)

        return room_data, status.HTTP_200_OK

    @action()
    async def leave_room(self, **kwargs):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        if hasattr(self, 'can_message'):
            delattr(self, 'can_message')
            return {'response': f'Leaved room {self.room.pk} successfully!'}, status.HTTP_200_OK
        raise BadRequest("Action 'leave_room' not allowed. You are not in the room")

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
            action=get_method_name(),
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
                action=get_method_name(),
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
        await self.check_admin_can_act()

        deleted_count = await self.delete_messages_in_db(msg_id_list)

        if deleted_count == 0:
            raise NotFound(f"Messages with ids: {msg_id_list} were not found! Nothing was deleted!")

        data = {
            'room_id': self.room.pk,
            'messages_ids': msg_id_list,
        }

        errors = []

        if deleted_count != len(msg_id_list):
            errors.append(
                "Not all of the requested messages were deleted! "
                "Check whether the ids are correct and messages belong to the current user's room!"
            )

        await reply_to_groups(
            groups=(self.room_group_name,),
            handler_name='data_to_groups',
            action=get_method_name(),
            data=data,
            errors=errors,
            status=status.HTTP_200_OK,
            request_id=kwargs['request_id']
        )

    async def data_to_groups(self, event):
        await self.send_json(event['payload'])

    async def check_admin_can_act(self):
        """
        Check whether admin can create, edit and delete messages in room.

        If admin not connected to a room, then raises BadRequest exception.
        If room does not have brand with business subscription, then raises PermissionDenied exception.
        Otherwise, does nothing.
        """
        try:
            if not self.can_message:
                raise PermissionDenied(
                    "Action not allowed. "
                    "You cannot write to a chat that does not have brand with business subscription!"
                )
        except AttributeError:
            raise BadRequest("Action not allowed. You are not in the room!")

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
        return Message.objects.filter(pk=msg_id, user=self.scope['user']).update(text=text)

    @database_sync_to_async
    def delete_messages_in_db(self, msg_id_list: list[int]) -> int:
        """
        Delete messages from db. Can delete any message in current room.

        Args:
            msg_id_list: list of ids of message to delete

        Returns number of messages deleted
        """
        return Message.objects.filter(pk__in=msg_id_list, room=self.room).delete()[0]

    @database_sync_to_async
    def get_serialized_room(self, **kwargs):
        serializer = self.get_serializer(action_kwargs=kwargs, instance=self.room)
        return serializer.data

    @database_sync_to_async
    def get_serialized_message(self, message, **kwargs):
        serializer = self.get_serializer(action_kwargs=kwargs, instance=message)
        return serializer.data
