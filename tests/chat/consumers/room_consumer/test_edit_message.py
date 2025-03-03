from cities_light.models import Country, City
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.test import override_settings, TransactionTestCase, tag
from django.utils import timezone
from rest_framework import status

from core.apps.blacklist.models import BlackList
from core.apps.brand.models import Category, Brand, Match
from core.apps.chat.consumers import RoomConsumer, AdminRoomConsumer
from core.apps.chat.models import Room, Message
from core.apps.payments.models import Tariff, Subscription
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import get_websocket_communicator_for_user, join_room_communal, join_room

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class RoomConsumerEditMessageTestCase(TransactionTestCase, RoomConsumerActionsMixin):
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

        now = timezone.now()
        self.tariff = Tariff.objects.get(name='Lite Match')

        Subscription.objects.bulk_create([
            Subscription(
                brand=brand,
                tariff=self.tariff,
                start_date=now,
                end_date=now + relativedelta(months=self.tariff.duration.days // 30),
                is_active=True
            )
            for brand in [self.brand1, self.brand2]
        ])

        self.path = 'ws/chat/'
        self.accepted_protocol = 'chat'

        self.admin_path = 'ws/admin-chat/'
        self.admin_accepted_protocol = 'admin-chat'

    async def test_edit_message_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await User.objects.acreate(
            email=f'user3@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        brand = await Brand.objects.acreate(user=user_wo_active_sub, **self.brand_data)

        room = await Room.objects.acreate(type=Room.INSTANT)
        await room.participants.aset([user_wo_active_sub])

        msg = await Message.objects.acreate(
            text='test',
            user=user_wo_active_sub,
            room=room
        )

        now = timezone.now()

        # create active sub
        sub = await Subscription.objects.acreate(
            brand=brand,
            tariff=self.tariff,
            start_date=now,
            end_date=now + relativedelta(months=self.tariff.duration.days // 30),
            is_active=True
        )

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=user_wo_active_sub
        )

        # connect with active sub
        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            # make sub expired
            sub.end_date = now - relativedelta(days=1)
            await sub.asave()

            response = await self.edit_message(communicator, msg.id, 'edited')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

        await communicator.disconnect()

    async def test_edit_message_not_in_room_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        message = await Message.objects.acreate(
            text='asf',
            user=self.user1,
            room=room
        )

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.edit_message(communicator, message.id, 'edited')

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        # check that message text did not change
        msg = await Message.objects.aget(id=message.id)
        self.assertEqual(msg.text, message.text)

    async def test_edit_message_if_brand_in_blacklist_of_interlocutor_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        msg = await Message.objects.acreate(
            text='asf',
            user=self.user1,
            room=room
        )

        # brand2 blocks brand1
        await BlackList.objects.acreate(initiator=self.brand2, blocked=self.brand1)

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            response = await self.edit_message(communicator, msg.id, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_edit_message_if_interlocutor_in_blacklist_of_brand_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        msg = await Message.objects.acreate(
            text='asf',
            user=self.user1,
            room=room
        )

        # brand1 blocks brand2
        await BlackList.objects.acreate(initiator=self.brand1, blocked=self.brand2)

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            response = await self.edit_message(communicator, msg.id, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_edit_message_not_found(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        communicator1 = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        communicator2 = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user2
        )

        connected1, _ = await communicator1.connect()
        connected2, __ = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        async with join_room_communal([communicator1, communicator2], room.pk):
            response = await self.edit_message(communicator1, 0, 'edited')
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to second user

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)

            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_edit_message(self):
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT),
            Room(type=Room.SUPPORT),
        ])

        match_room, instant_room, support_room = rooms

        await match_room.participants.aset([self.user1, self.user2])
        await instant_room.participants.aset([self.user1, self.user2])
        await support_room.participants.aset([self.user1])

        await Match.objects.acreate(
            initiator=self.user1.brand,
            target=self.user2.brand,
            is_match=False,
            room=instant_room
        )

        messages = await Message.objects.abulk_create([
            Message(
                text='asf',
                user=self.user1,
                room=room
            )
            for room in rooms
        ])

        match_room_msg, instant_room_msg, support_room_msg = messages

        # initial admin (that was before the user connected to websocket)
        admin1 = await User.objects.acreate(
            email=f'admin_unique@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True,
            is_staff=True
        )

        communicator1 = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        communicator2 = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user2
        )

        admin_communicator1 = get_websocket_communicator_for_user(
            url_pattern=self.admin_path,
            path=self.admin_path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.admin_accepted_protocol],
            user=admin1
        )

        connected1, _ = await communicator1.connect()
        connected2, __ = await communicator2.connect()
        connected3, ___ = await admin_communicator1.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)
        self.assertTrue(connected3)

        # create another admin when user is already connected
        # admin2 must be added to the list of groups to which the message is sent
        admin2 = await User.objects.acreate(
            email=f'admin2_unique@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True,
            is_staff=True
        )

        admin_communicator2 = get_websocket_communicator_for_user(
            url_pattern=self.admin_path,
            path=self.admin_path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.admin_accepted_protocol],
            user=admin2
        )

        connected4, __ = await admin_communicator2.connect()

        self.assertTrue(connected4)

        async with join_room_communal([communicator1, communicator2], match_room.pk):
            edited_msg_text = 'edited'
            response1 = await self.edit_message(communicator1, match_room_msg.id, edited_msg_text)
            response2 = await communicator2.receive_json_from()

            # check that admins aren't notified about non-support room actions
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response1, response2]:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)
                self.assertEqual(response['data']['id'], match_room_msg.id)
                self.assertEqual(response1['data']['text'], edited_msg_text)

            msg = await Message.objects.aget(id=match_room_msg.id)
            self.assertEqual(msg.text, edited_msg_text)  # check that message text changed in db

        async with join_room_communal([communicator1, communicator2], instant_room.pk):
            edited_msg_text = 'edited'
            response1 = await self.edit_message(communicator1, instant_room_msg.id, edited_msg_text)
            response2 = await communicator2.receive_json_from()

            # check that admins aren't notified about non-support room actions
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response1, response2]:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)
                self.assertEqual(response['data']['id'], instant_room_msg.id)
                self.assertEqual(response1['data']['text'], edited_msg_text)

        async with join_room(communicator1, support_room.pk):
            edited_msg_text = 'edited'
            response = await self.edit_message(communicator1, support_room_msg.id, edited_msg_text)
            admin1_response = await admin_communicator1.receive_json_from()
            admin2_response = await admin_communicator2.receive_json_from()

            # check that only one notification is sent
            self.assertTrue(await communicator1.receive_nothing())
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response, admin1_response, admin2_response]:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)
                self.assertEqual(response['data']['id'], support_room_msg.id)
                self.assertEqual(response1['data']['text'], edited_msg_text)

        await communicator1.disconnect()
        await communicator2.disconnect()
        await admin_communicator1.disconnect()
        await admin_communicator2.disconnect()

    async def test_edit_message_of_another_user_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        message = await Message.objects.acreate(
            text='asf',
            user=self.user2,
            room=room
        )

        communicator1 = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        communicator2 = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user2
        )

        connected1, _ = await communicator1.connect()
        connected2, __ = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        async with join_room_communal([communicator1, communicator2], room.pk):
            response = await self.edit_message(communicator1, message.id, 'edited')
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to second user

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator1.disconnect()
        await communicator2.disconnect()
