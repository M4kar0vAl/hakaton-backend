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
class RoomConsumerEditMessageTestCase(TransactionTestCase):
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

    async def test_edit_message_not_in_room_not_allowed(self):
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
            'action': 'edit_message',
            'msg_id': message.id,
            'edited_msg_text': 'edited',
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)

        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        # check that message text did not change
        msg = await Message.objects.aget(id=message.id)
        self.assertEqual(msg.text, message.text)

    async def test_edit_message_not_found(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

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
            'action': 'edit_message',
            'msg_id': 0,
            'edited_msg_text': 'edited',
            'request_id': 1500000
        })

        response = await communicator1.receive_json_from()
        self.assertTrue(await communicator1.receive_nothing())  # check that nothing was sent to second user

        await communicator1.disconnect()
        await communicator2.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)

        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_edit_message(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        message = await Message.objects.acreate(
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
            'action': 'edit_message',
            'msg_id': message.id,
            'edited_msg_text': 'edited',
            'request_id': 1500000
        })

        response1 = await communicator1.receive_json_from()
        response2 = await communicator2.receive_json_from()

        await communicator1.disconnect()
        await communicator2.disconnect()

        self.assertEqual(response1['response_status'], status.HTTP_200_OK)
        self.assertEqual(response2['response_status'], status.HTTP_200_OK)  # second user should get the same message

        self.assertEqual(response1['data']['message_text'], 'edited')
        self.assertEqual(response2['data']['message_text'], 'edited')

        msg = await Message.objects.aget(id=message.id)
        self.assertEqual(msg.text, 'edited')

    async def test_edit_message_of_another_user_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        message = await Message.objects.acreate(
            text='asf',
            user=self.user2,
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
            'action': 'edit_message',
            'msg_id': message.id,
            'edited_msg_text': 'edited',
            'request_id': 1500000
        })

        response = await communicator1.receive_json_from()
        self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to second user

        await communicator1.disconnect()
        await communicator2.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)

        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])
