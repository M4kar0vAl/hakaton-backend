from cities_light.models import Country, City
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.test import override_settings, TransactionTestCase, tag
from django.utils import timezone
from rest_framework import status

from core.apps.brand.models import Category, Brand
from core.apps.chat.consumers import RoomConsumer
from core.apps.chat.models import Room, Message
from core.apps.payments.models import Tariff, Subscription
from tests.mixins import RoomConsumerActionsMixin
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
class RoomConsumerGetRoomsTestCase(TransactionTestCase, RoomConsumerActionsMixin):
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

    async def test_get_rooms_wo_active_sub_not_allowed(self):
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

        # make sub expired
        sub.end_date = now - relativedelta(days=1)
        await sub.asave()

        response = await self.get_rooms(communicator, 1)

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_get_rooms(self):
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT),
            Room(type=Room.SUPPORT),
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT)
        ])

        match_room, instant_room, support_room, match_room_1_deleted, instant_room_1_deleted = rooms

        await match_room.participants.aset([self.user1, self.user2])
        await instant_room.participants.aset([self.user1, self.user2])
        await support_room.participants.aset([self.user1])
        await match_room_1_deleted.participants.aset([self.user1])
        await instant_room_1_deleted.participants.aset([self.user1])

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

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.get_rooms(communicator, 1)

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        results = response['data']['results']

        self.assertEqual(len(results), len(rooms))

        match_room_resp = results[0]
        instant_room_resp = results[1]
        support_room_resp = results[2]
        match_room_1_deleted_resp = results[3]
        instant_room_1_deleted_resp = results[4]

        # check last messages
        self.assertIsNotNone(match_room_resp['last_message'])
        self.assertIsNotNone(instant_room_resp['last_message'])
        self.assertIsNone(support_room_resp['last_message'])
        self.assertIsNone(match_room_1_deleted_resp['last_message'])
        self.assertIsNone(instant_room_1_deleted_resp['last_message'])

        # check that returned last created message
        self.assertEqual(match_room_resp['last_message']['user'], self.user2.id)

        # check interlocutors brands
        # check match room
        self.assertEqual(len(match_room_resp['interlocutors_brand']), 1)
        self.assertEqual(match_room_resp['interlocutors_brand'][0]['id'], self.brand2.id)

        # check instant room
        self.assertEqual(len(instant_room_resp['interlocutors_brand']), 1)
        self.assertEqual(instant_room_resp['interlocutors_brand'][0]['id'], self.brand2.id)

        # check support room
        self.assertEqual(len(support_room_resp['interlocutors_brand']), 0)  # change to W2W agency

        # check match room with deleted interlocutor
        self.assertEqual(len(match_room_1_deleted_resp['interlocutors_brand']), 0)

        # check instant room with deleted interlocutor
        self.assertEqual(len(instant_room_1_deleted_resp['interlocutors_brand']), 0)

    async def test_get_rooms_does_not_return_rooms_of_other_brands(self):
        another_user = await User.objects.acreate(
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

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.get_rooms(communicator, 1)

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        self.assertFalse(response['data']['results'])

    async def test_get_rooms_pagination(self):
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH)
            for _ in range(120)
        ])

        for room in rooms:
            await room.participants.aset([self.user1, self.user2])

        message1 = await Message.objects.acreate(
            text='afasf',
            user=self.user1,
            room=rooms[10]
        )

        message2 = await Message.objects.acreate(
            text='afasf',
            user=self.user1,
            room=rooms[11]
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

        # page 1
        response = await self.get_rooms(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        count = response['data']['count']
        results = response['data']['results']
        next_ = response['data']['next']

        self.assertEqual(count, len(rooms))
        self.assertEqual(len(results), 100)
        self.assertEqual(next_, 2)

        # check ordering
        # rooms are ordered by the room last message's 'created_at' field descending
        self.assertEqual(results[0]['last_message']['id'], message2.id)
        self.assertEqual(results[1]['last_message']['id'], message1.id)

        # page 2
        response = await self.get_rooms(communicator, 2)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        results = response['data']['results']
        next_ = response['data']['next']

        self.assertEqual(len(results), 20)
        self.assertIsNone(next_)

        await communicator.disconnect()
