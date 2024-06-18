from typing import Type

from channels.db import database_sync_to_async
from django.db.models import QuerySet
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.mixins import ListModelMixin
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.serializers import Serializer

from core.apps.brand.models import Brand
from core.apps.chat.exceptions import BadRequest
from core.apps.chat.models import Room, Message
from core.apps.chat.permissions import IsAuthenticatedConnect, IsAdminUser
from core.apps.chat.serializers import RoomSerializer, MessageSerializer
from core.apps.chat.utils import send_to_groups


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
        self.brand = self.get_brand()
        self.brand_rooms = self.get_brand_rooms_pk_set()

        await self.add_group(self.user_group_name)

        await self.accept()

    @action()
    async def join_room(self, room_pk, **kwargs):
        if room_pk not in self.brand_rooms:
            # update related room_pks
            self.brand_rooms = self.get_brand_rooms_pk_set()

            # check again
            if room_pk not in self.brand_rooms:
                raise PermissionDenied('You cannot enter a room you are not a member of')

        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        self.room = self.get_object(pk=room_pk)
        self.room_group_name = f'room_{room_pk}'

        await self.add_group(self.room_group_name)

        serializer = self.get_serializer_class()(self.room)
        serializer.is_valid(raise_exception=True)

        return serializer.data, status.HTTP_200_OK

    @action()
    async def leave_room(self, **kwargs):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        if hasattr(self, 'room'):
            pk = self.room.pk
            delattr(self, 'room')
            return {'response': f'leaved room {pk} successfully!'}, status.HTTP_200_OK

        raise BadRequest('Action "leave_room" not allowed. You are not in the room')

    @action()
    async def create_message(self, msg_text: str, **kwargs):
        if not self.room:
            raise PermissionDenied('You cannot send a message when you are not in chat')

        message = await database_sync_to_async(Message.objects.create)(
            room=self.room,
            user=self.scope['user'],
            text=msg_text
        )

        serializer = self.get_serializer_class()(message)
        serializer.is_valid(raise_exception=True)

        await send_to_groups({'type': 'data_to_groups', 'data': serializer.data}, (self.room_group_name,))

        return serializer.data, status.HTTP_201_CREATED

    @action()
    async def current_room_info(self):
        serializer = self.get_serializer_class()(self.room)
        serializer.is_valid(raise_exception=True)

        await send_to_groups({'type': 'data_to_groups', 'data': serializer.data}, (self.user_group_name,))

        return serializer.data, status.HTTP_200_OK

    async def data_to_groups(self, event):
        await self.send_json(event['data'])

    @database_sync_to_async
    def get_brand(self) -> Brand:
        return Brand.objects.get(user=self.scope['user'])

    @database_sync_to_async
    def get_brand_rooms_pk_set(self):
        return set(self.brand.rooms.values_list('pk', flat=True))


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
    async def join_room(self, room_pk):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        self.room = self.get_object(pk=room_pk)
        self.room_group_name = f'room_{room_pk}'

        # check if there is business subscription brand
        self.can_message = self.check_can_message()

        await self.add_group(self.room_group_name)

        serializer = self.get_serializer_class()(self.room)
        serializer.is_valid(raise_exception=True)

        return serializer.data, status.HTTP_200_OK

    @action()
    async def leave_room(self):
        if hasattr(self, 'room_group_name'):
            await self.remove_group(self.room_group_name)

        if hasattr(self, 'can_message'):
            pk = self.room.pk
            delattr(self, 'can_message')
            return {'response': f'leaved room {pk} successfully!'}, status.HTTP_200_OK
        return BadRequest('Action "leave_room" not allowed. You are not in the room')

    @action()
    async def create_message(self, msg_text, **kwargs):
        try:
            if not self.can_message:
                raise PermissionDenied('You cannot write to a chat that does not have brand with business subscription')
        except AttributeError:
            raise PermissionDenied('You cannot send a message when you are not in chat')

        message = await database_sync_to_async(Message.objects.create)(
            room=self.room,
            user=self.scope['user'],
            text=msg_text
        )

        serializer = self.get_serializer_class()(message)
        serializer.is_valid(raise_exception=True)

        await send_to_groups({'type': 'data_to_groups', 'data': serializer.data}, (self.room_group_name,))

        return serializer.data, status.HTTP_201_CREATED

    async def data_to_groups(self, event):
        await self.send_json(event['data'])

    @database_sync_to_async
    def check_can_message(self):
        return any(
            self.room.participants.values_list('has_business', flat=True)
        )
