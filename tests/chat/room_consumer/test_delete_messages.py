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
class RoomConsumerDeleteMessagesTestCase(TransactionTestCase):
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

    async def test_delete_messages_not_in_room_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        message = await Message.objects.acreate(
            text='asf',
            user=self.user1,
            room=room
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
            'action': 'delete_messages',
            'msg_id_list': [message.id],
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)

        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        msg_exists = await Message.objects.filter(id=message.id).aexists()

        self.assertTrue(msg_exists)

    async def test_delete_messages_all_not_found(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        await Message.objects.acreate(
            text='asf',
            user=self.user1,
            room=room
        )

        access1 = AccessToken.for_user(self.user1)
        access2 = AccessToken.for_user(self.user2)

        communicator1 = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access1
        )

        communicator2 = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access2
        )

        connected1, subprotocol1 = await communicator1.connect()
        connected2, subprotocol2 = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        await communicator1.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        await communicator2.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        await communicator1.receive_json_from()
        await communicator2.receive_json_from()

        await communicator1.send_json_to({
            'action': 'delete_messages',
            'msg_id_list': [0, -1],
            'request_id': 1500000
        })

        response = await communicator1.receive_json_from()
        self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to the second user

        await communicator1.disconnect()
        await communicator2.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)

        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_delete_messages(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        messages = await Message.objects.abulk_create([
            Message(
                text='asf',
                user=self.user1,
                room=room
            ),
            Message(
                text='fahnj',
                user=self.user1,
                room=room
            )
        ])

        messages_ids = [msg.id for msg in messages]

        access1 = AccessToken.for_user(self.user1)
        access2 = AccessToken.for_user(self.user2)

        communicator1 = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access1
        )

        communicator2 = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access2
        )

        connected1, subprotocol1 = await communicator1.connect()
        connected2, subprotocol2 = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        await communicator1.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        await communicator2.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        await communicator1.receive_json_from()
        await communicator2.receive_json_from()

        await communicator1.send_json_to({
            'action': 'delete_messages',
            'msg_id_list': messages_ids,
            'request_id': 1500000
        })

        response1 = await communicator1.receive_json_from()
        response2 = await communicator2.receive_json_from()

        await communicator1.disconnect()
        await communicator2.disconnect()

        self.assertEqual(response1['response_status'], status.HTTP_200_OK)
        self.assertEqual(response2['response_status'], status.HTTP_200_OK)

        self.assertEqual(response1['data']['messages_ids'], messages_ids)
        self.assertEqual(response2['data']['messages_ids'], messages_ids)

        messages_exists = await Message.objects.filter(id__in=messages_ids).aexists()
        self.assertFalse(messages_exists)

    async def test_delete_messages_of_another_user_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        messages = await Message.objects.abulk_create([
            Message(
                text='asf',
                user=self.user2,
                room=room
            ),
            Message(
                text='fahnj',
                user=self.user2,
                room=room
            )
        ])

        messages_ids = [msg.id for msg in messages]

        access1 = AccessToken.for_user(self.user1)
        access2 = AccessToken.for_user(self.user2)

        communicator1 = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access1
        )

        communicator2 = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access2
        )

        connected1, subprotocol1 = await communicator1.connect()
        connected2, subprotocol2 = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        await communicator1.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        await communicator2.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        await communicator1.receive_json_from()
        await communicator2.receive_json_from()

        await communicator1.send_json_to({
            'action': 'delete_messages',
            'msg_id_list': messages_ids,
            'request_id': 1500000
        })

        response = await communicator1.receive_json_from()
        self.assertTrue(await communicator1.receive_nothing())  # check that nothing was sent to the second user

        await communicator1.disconnect()
        await communicator2.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)

        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        messages_exist = await Message.objects.filter(id__in=messages_ids).aexists()
        self.assertTrue(messages_exist)

    async def test_delete_messages_some_not_found(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        messages = await Message.objects.abulk_create([
            Message(
                text='asf',
                user=self.user1,
                room=room
            ),
            Message(
                text='fahnj',
                user=self.user1,
                room=room
            )
        ])

        existing_messages_ids = [msg.id for msg in messages]

        access1 = AccessToken.for_user(self.user1)
        access2 = AccessToken.for_user(self.user2)

        communicator1 = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access1
        )

        communicator2 = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access2
        )

        connected1, subprotocol1 = await communicator1.connect()
        connected2, subprotocol2 = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        await communicator1.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        await communicator2.send_json_to({
            'action': 'join_room',
            'room_pk': room.pk,
            'request_id': 1500000
        })

        await communicator1.receive_json_from()
        await communicator2.receive_json_from()

        await communicator1.send_json_to({
            'action': 'delete_messages',
            'msg_id_list': existing_messages_ids + [0],
            'request_id': 1500000
        })

        response = await communicator1.receive_json_from()
        self.assertTrue(await communicator1.receive_nothing())  # check that nothing was sent to the second user

        await communicator1.disconnect()
        await communicator2.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)

        self.assertTrue(response['errors'])
        self.assertIsNone(response['data'])

        existing_messages_num = await Message.objects.filter(id__in=existing_messages_ids).acount()
        self.assertEqual(existing_messages_num, len(messages))

    async def test_delete_messages_does_not_delete_messages_in_other_rooms(self):
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.MATCH)
        ])

        room1, room2 = rooms

        await room1.participants.aset([self.user1, self.user2])
        await room2.participants.aset([self.user1, self.user2])

        room2_messages = await Message.objects.abulk_create([
            Message(
                text='fahnj',
                user=self.user1,
                room=room2
            ),
            Message(
                text='fahnj',
                user=self.user1,
                room=room2
            )
        ])

        messages_ids = [msg.id for msg in room2_messages]

        access1 = AccessToken.for_user(self.user1)
        access2 = AccessToken.for_user(self.user2)

        communicator1 = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access1
        )

        communicator2 = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access2
        )

        connected1, subprotocol1 = await communicator1.connect()
        connected2, subprotocol2 = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        await communicator1.send_json_to({
            'action': 'join_room',
            'room_pk': room1.pk,
            'request_id': 1500000
        })

        await communicator2.send_json_to({
            'action': 'join_room',
            'room_pk': room1.pk,
            'request_id': 1500000
        })

        await communicator1.receive_json_from()
        await communicator2.receive_json_from()

        # try to delete messages in room2
        await communicator1.send_json_to({
            'action': 'delete_messages',
            'msg_id_list': messages_ids,
            'request_id': 1500000
        })

        response = await communicator1.receive_json_from()
        self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to the second user

        await communicator1.disconnect()
        await communicator2.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)

        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        messages_exist = await Message.objects.filter(id__in=messages_ids).aexists()
        self.assertTrue(messages_exist)
