from channels.db import database_sync_to_async
from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from core.apps.brand.models import Category, Brand
from core.apps.chat.consumers import RoomConsumer
from core.apps.chat.models import Room, Message
from tests.utils import get_websocket_communicator

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class RoomConsumerListTestCase(TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        self.user1 = User.objects.create_user(
            email=f'user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        self.user2 = User.objects.create_user(
            email=f'user2@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        country = Country.objects.create(name='Country', continent='EU')
        city = City.objects.create(name='City', country=country)

        self.brand_data = {
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

        self.brand1 = Brand.objects.create(user=self.user1, **self.brand_data)
        self.brand2 = Brand.objects.create(user=self.user2, **self.brand_data)

        self.path = 'ws/chat/'
        self.accepted_protocol = 'chat'

    async def test_list(self):
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT),
            Room(type=Room.SUPPORT)
        ])

        for room in rooms:
            if room.type == Room.SUPPORT:
                await room.participants.aset([self.user1])
            else:
                await room.participants.aset([self.user1, self.user2])

        await Message.objects.abulk_create([
            Message(
                text='test',
                user=self.user1,
                room=rooms[0]
            ),
            Message(
                text='test',
                user=self.user1,
                room=rooms[1]
            )
        ])

        await Message.objects.acreate(
            text='test',
            user=self.user2,
            room=rooms[0]
        )

        access = AccessToken.for_user(self.user1)

        communicator = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access
        )

        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        await communicator.send_json_to({
            'action': 'list',
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        self.assertEqual(len(response['data']), len(rooms))

        match_room = response['data'][0]
        instant_room = response['data'][1]
        support_room = response['data'][2]

        # check last messages
        self.assertIsNotNone(match_room['last_message'])
        self.assertIsNotNone(instant_room['last_message'])
        self.assertIsNone(support_room['last_message'])

        self.assertEqual(match_room['last_message']['user'], self.user2.id)  # check that returned last created message

        # check interlocutors brands
        self.assertTrue(match_room['interlocutors_brand'])
        self.assertTrue(instant_room['interlocutors_brand'])
        self.assertFalse(support_room['interlocutors_brand'])

        self.assertEqual(match_room['interlocutors_brand'][0]['id'], self.brand2.id)
        self.assertEqual(instant_room['interlocutors_brand'][0]['id'], self.brand2.id)

    async def test_list_does_not_return_rooms_of_other_brands(self):
        another_user = await database_sync_to_async(User.objects.create_user)(
            email=f'another_user@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT),
            Room(type=Room.SUPPORT)
        ])

        for room in rooms:
            if room.type == Room.SUPPORT:
                await room.participants.aset([another_user])
            else:
                await room.participants.aset([another_user, self.user2])

        access = AccessToken.for_user(self.user1)

        communicator = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access
        )

        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)

        await communicator.send_json_to({
            'action': 'list',
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        self.assertFalse(response['data'])
