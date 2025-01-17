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
class AdminRoomConsumerGetRoomMessagesTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):
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

    async def test_get_room_messages_not_in_room_not_allowed(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.get_room_messages(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_get_room_messages(self):
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
            Room(type=Room.INSTANT),
            Room(type=Room.SUPPORT),
            Room(type=Room.SUPPORT),
        ])

        match_room, instant_room, support_room, own_support_room = rooms

        await match_room.participants.aset([user1, user2])
        await instant_room.participants.aset([user1, user2])
        await support_room.participants.aset([user1])
        await own_support_room.participants.aset([self.admin_user])

        await Message.objects.abulk_create([
            Message(
                text='test',
                user=user1,
                room=match_room
            ),
            Message(
                text='test',
                user=user1,
                room=instant_room
            ),
            Message(
                text='test',
                user=user1,
                room=support_room
            ),
            Message(
                text='test',
                user=self.admin_user,
                room=own_support_room
            ),
        ])

        messages = await Message.objects.abulk_create([
            Message(
                text='test',
                user=user2,
                room=match_room
            ),
            Message(
                text='test',
                user=user2,
                room=instant_room
            ),
            Message(
                text='test',
                user=self.admin_user,
                room=support_room
            ),
            Message(
                text='test',
                user=self.admin_user,
                room=own_support_room
            ),
        ])

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
            user=user1
        )

        admin_connected, _ = await admin_communicator.connect()
        user_connected, __ = await user_communicator.connect()

        self.assertTrue(admin_connected)
        self.assertTrue(user_connected)

        async with join_room_communal([admin_communicator, user_communicator], match_room.pk) as responses:
            for response in responses:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            response = await self.get_room_messages(admin_communicator, 1)
            self.assertTrue(await user_communicator.receive_nothing())

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            messages_resp = response['data']['messages']

            self.assertEqual(len(messages_resp), 2)
            # check that messages ordered by created_at desc
            self.assertEqual(messages_resp[0]['id'], messages[0].id)

        async with join_room_communal([admin_communicator, user_communicator], instant_room.pk) as responses:
            for response in responses:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            response = await self.get_room_messages(admin_communicator, 1)
            self.assertTrue(await user_communicator.receive_nothing())

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            messages_resp = response['data']['messages']

            self.assertEqual(len(messages_resp), 2)
            # check that messages ordered by created_at desc
            self.assertEqual(messages_resp[0]['id'], messages[1].id)

        async with join_room_communal([admin_communicator, user_communicator], support_room.pk) as responses:
            for response in responses:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            response = await self.get_room_messages(admin_communicator, 1)
            self.assertTrue(await user_communicator.receive_nothing())

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            messages_resp = response['data']['messages']

            self.assertEqual(len(messages_resp), 2)
            # check that messages ordered by created_at desc
            self.assertEqual(messages_resp[0]['id'], messages[2].id)

        async with join_room(admin_communicator, own_support_room.pk) as response:
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            response = await self.get_room_messages(admin_communicator, 1)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            messages_resp = response['data']['messages']

            self.assertEqual(len(messages_resp), 2)
            # check that messages ordered by created_at desc
            self.assertEqual(messages_resp[0]['id'], messages[3].id)

        await admin_communicator.disconnect()
        await user_communicator.disconnect()

    async def test_get_room_messages_pagination(self):
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

        messages = await Message.objects.abulk_create([
            Message(
                text=f'test{i}',
                user=user,
                room=room
            )
            for i in range(110)
        ] + [
            Message(
                text=f'test{i}',
                user=self.admin_user,
                room=room
            )
            for i in range(110, 210)
        ])

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            # first page
            response = await self.get_room_messages(communicator, 1)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            self.assertEqual(response['data']['count'], len(messages))
            self.assertEqual(len(response['data']['messages']), 100)
            self.assertEqual(response['data']['next'], 2)

            # second page
            response = await self.get_room_messages(communicator, 2)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            self.assertEqual(len(response['data']['messages']), 100)
            self.assertEqual(response['data']['next'], 3)

            # third page
            response = await self.get_room_messages(communicator, 3)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            self.assertEqual(len(response['data']['messages']), 10)
            self.assertIsNone(response['data']['next'])

            # negative page number
            response = await self.get_room_messages(communicator, -1)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

            # page number is not a number
            response = await self.get_room_messages(communicator, 'asf')

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()
