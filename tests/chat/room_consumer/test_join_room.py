from cities_light.models import City, Country
from django.contrib.auth import get_user_model
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from core.apps.brand.models import Category, Brand
from core.apps.chat.consumers import RoomConsumer
from core.apps.chat.models import Room
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
class RoomConsumerJoinRoomTestCase(TransactionTestCase):
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

    async def test_join_room(self):
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT),
            Room(type=Room.SUPPORT),
        ])

        for room in rooms:
            if room.type == Room.SUPPORT:
                await room.participants.aset([self.user1])
            else:
                await room.participants.aset([self.user1, self.user2])

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

        match_room, instant_room, support_room = rooms

        # check join match room
        await communicator.send_json_to({
            'action': 'join_room',
            'room_pk': match_room.id,
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        await communicator.send_json_to({
            'action': 'leave_room',
            'request_id': 1500000
        })

        await communicator.receive_json_from()

        # check join instant room
        await communicator.send_json_to({
            'action': 'join_room',
            'room_pk': instant_room.id,
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        await communicator.send_json_to({
            'action': 'leave_room',
            'request_id': 1500000
        })

        await communicator.receive_json_from()

        # check join support room
        await communicator.send_json_to({
            'action': 'join_room',
            'room_pk': support_room.id,
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        await communicator.send_json_to({
            'action': 'leave_room',
            'request_id': 1500000
        })

        await communicator.receive_json_from()

        await communicator.disconnect()

    async def test_join_room_if_already_joined_another_one(self):
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.MATCH),
        ])

        for room in rooms:
            await room.participants.aset([self.user1, self.user2])

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

        room1, room2 = rooms

        # join room1
        await communicator.send_json_to({
            'action': 'join_room',
            'room_pk': room1.pk,
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        # join room2
        await communicator.send_json_to({
            'action': 'join_room',
            'room_pk': room2.pk,
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        await communicator.disconnect()

    async def test_join_the_same_room(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

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

        # join room
        await communicator.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        await communicator.receive_json_from()

        # try to rejoin room
        await communicator.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)

        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        # leave room
        await communicator.send_json_to({
            'action': 'leave_room',
            'request_id': 1500000
        })

        await communicator.receive_json_from()

        # join room
        await communicator.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

    async def test_join_room_not_a_member_of(self):
        room = await Room.objects.acreate(type=Room.MATCH)

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
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])
