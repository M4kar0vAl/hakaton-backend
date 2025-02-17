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
class RoomConsumerGetRoomMessagesTestCase(TransactionTestCase, RoomConsumerActionsMixin):
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

    async def test_get_room_messages_wo_active_sub_not_allowed(self):
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

        async with join_room(communicator, room.pk):
            # make sub expired
            sub.end_date = now - relativedelta(days=1)
            await sub.asave()

            response = await self.get_room_messages(communicator, 1)

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

        await communicator.disconnect()

    async def test_get_room_messages_not_in_room_not_allowed(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.get_room_messages(communicator, 1)

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertTrue(response['errors'])
        self.assertIsNone(response['data'])

    async def test_get_room_messages(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        messages = await Message.objects.abulk_create([
            Message(
                text='asfa',
                user=self.user1,
                room=room
            ),
            Message(
                text='asfa',
                user=self.user2,
                room=room
            ),
            Message(
                text='asfa',
                user=self.user2,
                room=room
            )
        ])

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
            response = await self.get_room_messages(communicator1, 1)
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to the second user

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            self.assertEqual(len(response['data']['results']), len(messages))

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_get_room_messages_returns_only_current_room_messages(self):
        room1 = await Room.objects.acreate(type=Room.MATCH)
        room2 = await Room.objects.acreate(type=Room.MATCH)

        await room1.participants.aset([self.user1, self.user2])
        await room2.participants.aset([self.user1, self.user2])

        room1_messages = await Message.objects.abulk_create([
            Message(
                text='asfa',
                user=self.user1,
                room=room1
            ),
            Message(
                text='asfa',
                user=self.user2,
                room=room1
            ),
            Message(
                text='asfa',
                user=self.user2,
                room=room1
            )
        ])

        await Message.objects.abulk_create([
            Message(
                text='asfa',
                user=self.user1,
                room=room2
            ),
            Message(
                text='asfa',
                user=self.user2,
                room=room2
            )
        ])

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
            response = await self.get_room_messages(communicator, 1)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            self.assertEqual(len(response['data']['results']), len(room1_messages))

        await communicator.disconnect()

    async def test_get_room_messages_pagination(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        messages = await Message.objects.abulk_create(
            [
                Message(
                    text=f'msg_{i}',
                    user=self.user1,
                    room=room
                )
                for i in range(109)
            ] + [
                Message(
                    text=f'msg_{i}',
                    user=self.user2,
                    room=room
                )
                for i in range(109, 220)
            ]
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
            # first page
            response = await self.get_room_messages(communicator, 1)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            self.assertEqual(response['data']['count'], len(messages))
            self.assertEqual(len(response['data']['results']), 100)
            self.assertEqual(response['data']['next'], 2)

            # second page
            response = await self.get_room_messages(communicator, 2)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            self.assertEqual(len(response['data']['results']), 100)
            self.assertEqual(response['data']['next'], 3)

            # third page
            response = await self.get_room_messages(communicator, 3)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            self.assertEqual(len(response['data']['results']), 20)
            self.assertIsNone(response['data']['next'])

            # negative page number
            response = await self.get_room_messages(communicator, -1)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertTrue(response['errors'])
            self.assertIsNone(response['data'])

            # page number is not a number
            response = await self.get_room_messages(communicator, 'asf')

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertTrue(response['errors'])
            self.assertIsNone(response['data'])

        await communicator.disconnect()
