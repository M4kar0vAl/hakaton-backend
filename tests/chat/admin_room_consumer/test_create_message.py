from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.test import tag, TransactionTestCase, override_settings
from rest_framework import status

from core.apps.brand.models import Category, Brand
from core.apps.chat.consumers import AdminRoomConsumer, RoomConsumer
from core.apps.chat.models import Room, Message
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import join_room, get_websocket_communicator_for_user, join_room_communal

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerCreateMessageTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):
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

    async def test_create_message_not_in_room_not_allowed(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.create_message(communicator, 'test')

        self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message_not_in_support_room_not_allowed(self):
        users = await User.objects.abulk_create([
            User(
                email=f'user{i}@example.com',
                phone='+79993332211',
                fullname='Юзеров Юзер Юзерович',
                password='Pass!234',
                is_active=True
            )
            for i in range(1, 3)
        ])

        user1, user2 = users

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

        await Brand.objects.abulk_create([Brand(user=user, **brand_data) for user in users])

        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT)
        ])

        match_room, instant_room = rooms

        await match_room.participants.aset([user1, user2])
        await instant_room.participants.aset([user1, user2])

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, match_room.id):
            response = await self.create_message(communicator, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        async with join_room(communicator, instant_room.id):
            response = await self.create_message(communicator, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message(self):
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

        rooms = await Room.objects.abulk_create([
            Room(type=Room.SUPPORT),
            Room(type=Room.SUPPORT)
        ])

        support_room, own_support_room = rooms

        await support_room.participants.aset([user])
        await own_support_room.participants.aset([self.admin_user])

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

        async with join_room_communal([admin_communicator, user_communicator], support_room.id):
            msg_text = 'test'
            admin_response = await self.create_message(admin_communicator, msg_text)
            user_response = await user_communicator.receive_json_from()  # check that user receives message

            self.assertEqual(admin_response['response_status'], status.HTTP_201_CREATED)
            self.assertEqual(user_response['response_status'], status.HTTP_201_CREATED)

            self.assertEqual(admin_response['data']['text'], msg_text)
            self.assertEqual(user_response['data']['text'], msg_text)

            msg_id = admin_response['data']['id']
            try:
                msg = await Message.objects.filter(room=support_room).aget()
            except (Message.DoesNotExist, Message.MultipleObjectReturned):
                msg = None

            self.assertIsNotNone(msg)
            self.assertEqual(msg.id, msg_id)

        await user_communicator.disconnect()

        async with join_room(admin_communicator, own_support_room.id):
            msg_text = 'test'
            response = await self.create_message(admin_communicator, msg_text)

            self.assertEqual(response['response_status'], status.HTTP_201_CREATED)

            self.assertEqual(response['data']['text'], msg_text)

            msg_id = response['data']['id']
            try:
                msg = await Message.objects.filter(room=own_support_room).aget()
            except (Message.DoesNotExist, Message.MultipleObjectReturned):
                msg = None

            self.assertIsNotNone(msg)
            self.assertEqual(msg.id, msg_id)

        await admin_communicator.disconnect()
