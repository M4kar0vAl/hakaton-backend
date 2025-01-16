from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.brand.models import Category, Brand
from core.apps.chat.consumers import AdminRoomConsumer, RoomConsumer
from core.apps.chat.models import Room
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import get_websocket_communicator_for_user

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerLeaveRoomTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):
    serialized_rollback = True

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email=f'admin_user@example.com',
            phone='+79993332211',
            fullname='Админов Админ Админович',
            password='Pass!234',
            is_active=True
        )

        self.path = 'ws/admin-chat/'
        self.accepted_protocol = 'admin-chat'

        self.user_path = 'ws/chat/'
        self.user_accepted_protocol = 'chat'

    async def test_leave_room_not_in_room(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.leave_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_leave_room(self):
        user = await User.objects.acreate(
            email=f'user@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        country = await Country.objects.acreate(name='Country', continent='EU')
        city = await City.objects.acreate(name='City', country=country)

        brand_data = {
            'tg_nickname': '@asfhbnaf',
            'city': city,
            'name': 'brand1',
            'position': 'position',
            'category': await Category.objects.aget(id=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        await Brand.objects.acreate(user=user, **brand_data)

        room = await Room.objects.acreate(type=Room.SUPPORT)

        await room.participants.aset([user])

        admin_communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        user_communicator = get_websocket_communicator_for_user(
            url_pattern=self.user_path,
            path=self.user_path,
            consumer_class=RoomConsumer,
            protocols=[self.user_accepted_protocol],
            user=user
        )

        admin_connected, _ = await admin_communicator.connect()
        user_connected, __ = await user_communicator.connect()

        self.assertTrue(admin_connected)
        self.assertTrue(user_connected)

        await self.join_room(admin_communicator, room.pk)
        await self.join_room(user_communicator, room.pk)

        response = await self.leave_room(admin_communicator)
        self.assertTrue(await user_communicator.receive_nothing())  # check that nothing was sent to the second user

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        await admin_communicator.disconnect()
        await user_communicator.disconnect()
