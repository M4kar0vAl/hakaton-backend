from channels.db import database_sync_to_async
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.mixins import ListModelMixin
from rest_framework import status

from core.apps.brand.models import Brand
from core.apps.chat.models import Room, Message
from core.apps.chat.serializers import RoomSerializer, MessageSerializer


class RoomConsumer(ListModelMixin,
                   GenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = "pk"

    async def connect(self):
        self.user_group_name = f'user_{self.scope["user"].pk}'

        await self.add_group(self.user_group_name)

        await self.accept()

    @action()
    async def join_room(self, room_pk, **kwargs):
        self.room = self.get_object(pk=room_pk)
        self.brand = self.get_brand()
        self.room_group_name = f'room_{room_pk}'

        await self.add_group(self.room_group_name)

        serializer = self.get_serializer_class()(self.room)

        return serializer.data, status.HTTP_200_OK

    @action()
    async def leave_room(self, **kwargs):
        await self.remove_group(self.room_group_name)

    @action()
    async def create_message(self, msg_text: str, **kwargs):
        message = await database_sync_to_async(Message.objects.create)(
            room=self.room,
            user=self.brand,
            text=msg_text
        )

        serializer = MessageSerializer(message)

        return serializer.data, status.HTTP_201_CREATED

    @database_sync_to_async
    def get_brand(self) -> Brand:
        return Brand.objects.get(user=self.scope['user'])
