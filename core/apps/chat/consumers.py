from channels.db import database_sync_to_async
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer

from core.apps.brand.models import Brand
from core.apps.brand.serializers import BrandGetSerializer
from core.apps.chat.models import Room, Message
from core.apps.chat.serializers import RoomSerializer


class RoomConsumer(GenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = "pk"

    async def connect(self):
        self.room_pk = self.scope["url_route"]["kwargs"]["pk"]
        self.room_group_name = f'room_{self.room_pk}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @action()
    async def join_room(self, pk, **kwargs):
        self.room_subscribe = pk
        await self.add_brand_to_room(pk)

    @action()
    async def leave_room(self, pk, **kwargs):
        await self.remove_brand_from_room(pk)

    @action()
    async def create_message(self, message, **kwargs):
        room = await self.get_room(pk=self.room_subscribe)
        await database_sync_to_async(Message.objects.create)(
            room=room,
            user=self.scope["user"],
            text=message
        )

    @database_sync_to_async
    def get_room(self, pk: int) -> Room:
        return Room.objects.get(pk=pk)

    @database_sync_to_async
    def current_brands(self, room: Room):
        return [BrandGetSerializer(brand).data for brand in room.participants.all()]

    @database_sync_to_async
    def remove_brand_from_room(self, room_pk):
        self.get_brand().rooms.remove(room_pk)

    @database_sync_to_async
    def add_brand_to_room(self, pk):
        brand = self.get_brand()
        if not brand.rooms.filter(pk=pk).exists():
            brand.rooms.add(self.get_room(pk=pk))

    @database_sync_to_async
    def get_brand(self):
        return Brand.objects.get(user=self.scope['user'])
