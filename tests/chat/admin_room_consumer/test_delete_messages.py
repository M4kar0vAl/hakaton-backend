from cities_light.models import Country, City
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.test import tag, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework import status

from core.apps.brand.models import Category, Brand
from core.apps.chat.consumers import AdminRoomConsumer, RoomConsumer
from core.apps.chat.models import Room, Message
from core.apps.payments.models import Tariff, Subscription
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import join_room, get_websocket_communicator_for_user, join_room_communal

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerDeleteMessagesTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):
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

        self.user_path = 'ws/chat/'
        self.user_accepted_protocol = 'chat'

    async def test_delete_messages_not_in_room_not_allowed(self):
        room = await Room.objects.acreate(type=Room.SUPPORT)

        await room.participants.aset([self.admin_user])

        msg = await Message.objects.acreate(
            text='test',
            user=self.admin_user,
            room=room
        )

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.delete_messages(communicator, [msg.id])

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_delete_messages(self):
        user = await User.objects.acreate(
            email=f'user@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        country = await Country.objects.acreate(name='Country', continent='EU')
        city = await City.objects.acreate(name='City', country=country)

        brand_data = {
            'tg_nickname': '@asfhbnaf',
            'city': city,
            'name': 'brand1',
            'position': 'position',
            'category': await Category.objects.aget(id=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        brand = await Brand.objects.acreate(user=user, **brand_data)

        now = timezone.now()
        tariff = await Tariff.objects.aget(name='Lite Match')

        await Subscription.objects.acreate(
            brand=brand,
            tariff=tariff,
            start_date=now,
            end_date=now + relativedelta(months=tariff.duration.days // 30),
            is_active=True
        )

        rooms = await Room.objects.abulk_create([
            Room(type=Room.SUPPORT),
            Room(type=Room.SUPPORT)
        ])

        support_room, own_support_room = rooms

        await support_room.participants.aset([user])
        await own_support_room.participants.aset([self.admin_user])

        messages = await Message.objects.abulk_create([
            Message(
                text='test',
                user=self.admin_user,
                room=support_room
            ),
            Message(
                text='test',
                user=self.admin_user,
                room=own_support_room
            ),
            Message(
                text='test',
                user=self.admin_user,
                room=own_support_room
            )
        ])

        support_room_msg, *own_support_room_msgs = messages

        admin_communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        user_communicator = get_websocket_communicator_for_user(
            url_pattern=self.user_path,
            path=self.user_path,
            consumer_class=RoomConsumer,
            protocols=[self.user_accepted_protocol],
            user=user
        )

        admin_connected, _ = await admin_communicator.connect()
        user_connected, __ = await user_communicator.connect()

        self.assertTrue(admin_connected)
        self.assertTrue(user_connected)

        async with join_room_communal([admin_communicator, user_communicator], support_room.id):
            admin_response = await self.delete_messages(admin_communicator, [support_room_msg.id])
            user_response = await user_communicator.receive_json_from()

            self.assertEqual(admin_response['response_status'], status.HTTP_200_OK)
            self.assertEqual(user_response['response_status'], status.HTTP_200_OK)

            self.assertEqual(admin_response['data']['messages_ids'], [support_room_msg.id])
            self.assertEqual(user_response['data']['messages_ids'], [support_room_msg.id])

            # check that messages were deleted from db
            self.assertFalse(await Message.objects.filter(id__in=[support_room_msg.id]).aexists())

        await user_communicator.disconnect()

        async with join_room(admin_communicator, own_support_room.id):
            own_support_room_msgs_ids = [msg.id for msg in own_support_room_msgs]
            response = await self.delete_messages(admin_communicator, own_support_room_msgs_ids)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            self.assertEqual(response['data']['messages_ids'], own_support_room_msgs_ids)

            # check that messages were deleted from db
            self.assertFalse(await Message.objects.filter(id__in=own_support_room_msgs_ids).aexists())

        await admin_communicator.disconnect()

    async def test_delete_messages_all_not_found(self):
        room = await Room.objects.acreate(type=Room.SUPPORT)

        await room.participants.aset([self.admin_user])

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, room.id):
            response = await self.delete_messages(communicator, [0, -1])

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_delete_messages_some_not_found(self):
        room = await Room.objects.acreate(type=Room.SUPPORT)

        await room.participants.aset([self.admin_user])

        msg = await Message.objects.acreate(
            text='test',
            user=self.admin_user,
            room=room
        )

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, room.id):
            response = await self.delete_messages(communicator, [msg.id, -1])

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

            # check that existing message was not deleted
            self.assertTrue(await Message.objects.filter(id=msg.id).aexists())

        await communicator.disconnect()

    async def test_delete_messages_of_another_user_not_allowed(self):
        user = await User.objects.acreate(
            email=f'user@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        country = await Country.objects.acreate(name='Country', continent='EU')
        city = await City.objects.acreate(name='City', country=country)

        brand_data = {
            'tg_nickname': '@asfhbnaf',
            'city': city,
            'name': 'brand1',
            'position': 'position',
            'category': await Category.objects.aget(id=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        await Brand.objects.acreate(user=user, **brand_data)

        room = await Room.objects.acreate(type=Room.SUPPORT)

        await room.participants.aset([user])

        msg = await Message.objects.acreate(
            text='test',
            user=user,
            room=room
        )

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, room.id):
            response = await self.delete_messages(communicator, [msg.id])

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

            self.assertTrue(await Message.objects.filter(id=msg.id).aexists())

        await communicator.disconnect()

    async def test_delete_messages_not_in_support_room_not_allowed(self):
        user = await User.objects.acreate(
            email=f'user@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        country = await Country.objects.acreate(name='Country', continent='EU')
        city = await City.objects.acreate(name='City', country=country)

        brand_data = {
            'tg_nickname': '@asfhbnaf',
            'city': city,
            'name': 'brand1',
            'position': 'position',
            'category': await Category.objects.aget(id=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        await Brand.objects.acreate(user=user, **brand_data)

        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT)
        ])

        match_room, instant_room = rooms

        await match_room.participants.aset([user])
        await instant_room.participants.aset([user])

        messages = await Message.objects.abulk_create([
            Message(
                text='test',
                user=user,
                room=match_room
            ),
            Message(
                text='test',
                user=user,
                room=instant_room
            )
        ])

        match_room_msg, instant_room_msg = messages

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, match_room.pk):
            response = await self.delete_messages(communicator, [match_room_msg.id])

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        async with join_room(communicator, instant_room.pk):
            response = await self.delete_messages(communicator, [instant_room_msg.id])

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()
