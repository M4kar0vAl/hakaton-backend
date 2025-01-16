from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.test import tag, TransactionTestCase, override_settings
from rest_framework import status

from core.apps.brand.models import Category, Brand
from core.apps.chat.consumers import AdminRoomConsumer
from core.apps.chat.models import Room
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import join_room, get_websocket_communicator_for_user

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerJoinRoomTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):
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

        users = User.objects.bulk_create([
            User(
                email=f'user{i}@example.com',
                phone='+79993332211',
                fullname='Юзеров Юзер Юзерович',
                password='Pass!234',
                is_active=True
            )
            for i in range(1, 3)
        ])

        self.user1 = users[0]
        self.user2 = users[1]

        country = Country.objects.create(name='Country', continent='EU')
        city = City.objects.create(name='City', country=country)

        brand_data = {
            'tg_nickname': '@asfhbnaf',
            'city': city,
            'name': 'brand1',
            'position': 'position',
            'category': Category.objects.get(id=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        Brand.objects.bulk_create([Brand(user=user, **brand_data) for user in users])

        rooms = Room.objects.bulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT),
            Room(type=Room.SUPPORT),
            Room(type=Room.SUPPORT),
        ])

        self.match_room = rooms[0]
        self.instant_room = rooms[1]
        self.support_room = rooms[2]
        self.own_support_room = rooms[3]

        self.match_room.participants.set([self.user1, self.user2])
        self.instant_room.participants.set([self.user1, self.user2])
        self.support_room.participants.set([self.user1])
        self.own_support_room.participants.set([self.admin_user])

    async def test_join_room(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        # join match room
        async with join_room(communicator, self.match_room.pk) as response:
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

        # join instant room
        async with join_room(communicator, self.instant_room.pk) as response:
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

        # join support room
        async with join_room(communicator, self.support_room.pk) as response:
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

        # join own support room
        async with join_room(communicator, self.own_support_room.pk) as response:
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

        await communicator.disconnect()

    async def test_cannot_join_the_same_room(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        # ----------MATCH room----------
        async with join_room(communicator, self.match_room.pk):
            response = await self.join_room(communicator, self.match_room.pk)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        # ----------INSTANT room----------
        async with join_room(communicator, self.instant_room.pk):
            response = await self.join_room(communicator, self.instant_room.pk)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        # ----------SUPPORT room----------
        async with join_room(communicator, self.support_room.pk):
            response = await self.join_room(communicator, self.support_room.pk)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        # ----------OWN SUPPORT room----------
        async with join_room(communicator, self.own_support_room.pk):
            response = await self.join_room(communicator, self.own_support_room.pk)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_cannot_join_another_room_before_leaving_the_previous_one(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, self.support_room.pk):
            # try to join MATCH room
            response = await self.join_room(communicator, self.match_room.pk)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)

            # try to join INSTANT room
            response = await self.join_room(communicator, self.instant_room.pk)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)

            # try to join OWN SUPPORT room
            response = await self.join_room(communicator, self.own_support_room.pk)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)

        await communicator.disconnect()
