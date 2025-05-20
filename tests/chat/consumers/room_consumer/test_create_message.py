from importlib.metadata import always_iterable

from cities_light.models import Country, City
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.test import override_settings, TransactionTestCase, tag
from django.utils import timezone
from rest_framework import status

from core.apps.blacklist.models import BlackList
from core.apps.brand.models import Category, Brand, Match
from core.apps.chat.consumers import RoomConsumer, AdminRoomConsumer
from core.apps.chat.models import Room, Message, MessageAttachment
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
class RoomConsumerCreateMessageTestCase(TransactionTestCase, RoomConsumerActionsMixin):
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
        self.tariff_relativedelta = self.tariff.get_duration_as_relativedelta()

        Subscription.objects.bulk_create([
            Subscription(
                brand=brand,
                tariff=self.tariff,
                start_date=now,
                end_date=now + self.tariff_relativedelta,
                is_active=True
            )
            for brand in [self.brand1, self.brand2]
        ])

        self.path = 'ws/chat/'
        self.accepted_protocol = 'chat'

        self.admin_path = 'ws/admin-chat/'
        self.admin_accepted_protocol = 'admin-chat'

    async def test_create_message_wo_active_sub_not_allowed(self):
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

        now = timezone.now()

        # create active sub
        sub = await Subscription.objects.acreate(
            brand=brand,
            tariff=self.tariff,
            start_date=now,
            end_date=now + self.tariff_relativedelta,
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

            response = await self.create_message(communicator, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

        await communicator.disconnect()

    async def test_create_message_not_in_room_not_allowed(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.create_message(communicator, 'asf')

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_create_message_if_brand_in_blacklist_of_interlocutor_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

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
            response = await self.create_message(communicator, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message_if_interlocutor_in_blacklist_of_brand_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

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
            response = await self.create_message(communicator, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message(self):
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
            msg_text = 'test'
            response1 = await self.create_message(communicator1, msg_text)
            response2 = await communicator2.receive_json_from()

            # check that admins aren't notified about non-support room actions
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response1, response2]:
                self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
                self.assertEqual(response['data']['text'], msg_text)
                self.assertEqual(response['data']['room'], match_room.pk)

        async with join_room_communal([communicator1, communicator2], instant_room.pk):
            msg_text = 'test'
            response1 = await self.create_message(communicator1, msg_text)
            response2 = await communicator2.receive_json_from()

            # check that admins aren't notified about non-support room actions
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response1, response2]:
                self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
                self.assertEqual(response['data']['text'], msg_text)
                self.assertEqual(response['data']['room'], instant_room.pk)

        async with join_room(communicator1, support_room.pk):
            msg_text = 'test'
            response1 = await self.create_message(communicator1, msg_text)
            admin1_response = await admin_communicator1.receive_json_from()
            admin2_response = await admin_communicator2.receive_json_from()

            # check that only one notification is sent
            self.assertTrue(await communicator1.receive_nothing())
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            # check that both admins were notified
            for response in [response1, admin1_response, admin2_response]:
                self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
                self.assertEqual(response['data']['text'], msg_text)
                self.assertEqual(response['data']['room'], support_room.pk)

        await communicator1.disconnect()
        await communicator2.disconnect()
        await admin_communicator1.disconnect()
        await admin_communicator2.disconnect()

    async def test_create_message_instant_room_not_allowed_if_message_by_user_already_created(self):
        room = await Room.objects.acreate(type=Room.INSTANT)

        await room.participants.aset([self.user1, self.user2])

        await Match.objects.acreate(
            initiator=self.user1.brand,
            target=self.user2.brand,
            is_match=False,
            room=room
        )

        await Message.objects.acreate(
            text='asd',
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

        async with join_room(communicator, room.pk):
            response = await self.create_message(communicator, 'asf')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message_in_instant_room_user_is_not_the_initiator_of_coop(self):
        room = await Room.objects.acreate(type=Room.INSTANT)

        await room.participants.aset([self.user1, self.user2])

        await Match.objects.acreate(
            initiator=self.user1.brand,
            target=self.user2.brand,
            is_match=False,
            room=room
        )

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user2
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            response = await self.create_message(communicator, 'asf')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message_with_attachments(self):
        room = await Room.objects.acreate(type=Room.MATCH)
        await room.participants.aset([self.user1, self.user2])

        attachments = await MessageAttachment.objects.abulk_create([
            MessageAttachment(file='file1'),
            MessageAttachment(file='file2'),
        ])
        attachments_ids = [a.id for a in attachments]

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
        connected2, _ = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        async with join_room_communal([communicator1, communicator2], room.pk):
            response1 = await self.create_message(communicator1, 'any text', attachments_ids)
            response2 = await communicator2.receive_json_from()

            for response in [response1, response2]:
                response_attachments_ids = [a['id'] for a in response['data']['attachments']]

                self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
                self.assertEqual(attachments_ids, response_attachments_ids)

            msg_id = response1['data']['id']

            # check that attachments were connected to the message
            self.assertEqual(
                await MessageAttachment.objects.filter(id__in=attachments_ids, message_id=msg_id).acount(),
                2
            )

        await communicator1.disconnect()
        await communicator2.disconnect()
