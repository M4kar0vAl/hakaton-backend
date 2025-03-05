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
from tests.utils import get_websocket_communicator_for_user, join_room

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class RoomConsumerGetSupportRoomTestCase(TransactionTestCase, RoomConsumerActionsMixin):
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

    async def test_get_support_room_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await User.objects.acreate(
            email=f'user3@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        brand = await Brand.objects.acreate(user=user_wo_active_sub, **self.brand_data)

        room = await Room.objects.acreate(type=Room.SUPPORT)
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

        response = await self.get_support_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

        await communicator.disconnect()

    async def test_get_support_room(self):
        room = await Room.objects.acreate(type=Room.SUPPORT)

        await room.participants.aset([self.user1])

        msg = await Message.objects.acreate(
            text='test',
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

        response = await self.get_support_room(communicator)

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        room_id = response['data']['id']
        interlocutors = response['data']['interlocutors']
        last_message = response['data']['last_message']

        self.assertEqual(room_id, room.id)
        self.assertFalse(interlocutors)
        self.assertEqual(last_message['id'], msg.id)

    async def test_get_support_room_if_does_not_exist(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.get_support_room(communicator)

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_201_CREATED)

        room_id = response['data']['id']
        try:
            room = await Room.objects.prefetch_related('participants').aget(id=room_id)
        except Room.DoesNotExist:
            room = None

        self.assertIsNotNone(room)
        self.assertEqual(room.type, Room.SUPPORT)

        interlocutors = response['data']['interlocutors']
        last_message = response['data']['last_message']

        self.assertFalse(interlocutors)
        self.assertIsNone(last_message)

        participants = room.participants.all()

        self.assertEqual(len(participants), 1)
        self.assertEqual(participants[0].id, self.user1.id)

    async def test_get_support_room_if_in_room(self):
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.SUPPORT)
        ])

        room1, support_room = rooms

        await room1.participants.aset([self.user1, self.user2])
        await support_room.participants.aset([self.user1])

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, room1.pk):
            response = await self.get_support_room(communicator)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            room_id = response['data']['id']
            interlocutors = response['data']['interlocutors']

            self.assertEqual(room_id, support_room.id)
            self.assertFalse(interlocutors)

        await communicator.disconnect()
