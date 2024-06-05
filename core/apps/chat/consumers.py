from channels.db import database_sync_to_async
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer

from core.apps.brand.models import Brand
from core.apps.chat.models import Room, Message
from core.apps.chat.serializers import RoomSerializer


class RoomConsumer(GenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = "pk"

    async def connect(self):
        self.room_pk = self.scope["url_route"]["kwargs"]["pk"]
        self.room_group_name = f'room_{self.room_pk}'
        self.brand = self.get_brand()
        self.room = self.get_room()

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # переопределил reply, чтобы он отправлял данные всем в группе
    # (по умолчанию, вроде, возвращает только тому, кто отправил на сервер)
    async def reply(
            self, action: str, data=None, errors=None, status=200, request_id=None
    ):
        if errors is None:
            errors = []

        payload = {
            "errors": errors,
            "data": data,
            "action": action,
            "response_status": status,
            "request_id": request_id,
        }

        await self.channel_layer.group_send(self.room_group_name, payload)

    @action()
    async def join_room(self, pk, **kwargs):
        self.add_brand_to_room(pk)

    @action()
    async def leave_room(self, pk, **kwargs):
        self.remove_brand_from_room(pk)

    @action()
    async def create_message(self, message, **kwargs):
        await database_sync_to_async(Message.objects.create)(
            room=self.room,
            user=self.brand,
            text=message
        )

    @database_sync_to_async
    def get_room(self, pk: int) -> Room:
        return Room.objects.get(pk=pk)

    @database_sync_to_async
    def remove_brand_from_room(self, room_pk):
        self.brand.rooms.remove(room_pk)

    @database_sync_to_async
    def add_brand_to_room(self, room_pk):
        brand = self.brand
        if not brand.rooms.filter(pk=room_pk).exists():
            brand.rooms.add(room_pk)

    @database_sync_to_async
    def get_brand(self) -> Brand:
        return Brand.objects.get(user=self.scope['user'])
