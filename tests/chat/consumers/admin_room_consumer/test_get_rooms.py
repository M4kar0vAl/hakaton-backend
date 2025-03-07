from channels.db import database_sync_to_async
from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.brand.models import Brand, Category
from core.apps.chat.consumers import AdminRoomConsumer
from core.apps.chat.models import Room, Message
from tests.mixins import AdminRoomConsumerActionsMixin
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
class AdminRoomConsumerGetRoomsTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):
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

    async def test_get_rooms(self):
        users = await User.objects.abulk_create([
            User(
                email=f'user{i}@example.com',
                phone='+79993332211',
                fullname='Юзеров Юзер Юзерович',
                password='Pass!234',
                is_active=True
            )
            for i in range(1, 3)
        ])

        user1, user2 = users

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

        await Brand.objects.abulk_create([Brand(user=user, **brand_data) for user in users])

        rooms = await Room.objects.abulk_create([
            Room(type=Room.SUPPORT),
            Room(type=Room.SUPPORT),
            Room(type=Room.SUPPORT),
            Room(type=Room.SUPPORT),
            Room(type=Room.MATCH),
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT),
            Room(type=Room.INSTANT)
        ])

        (support_room1,
         support_room2,
         own_support_room,
         support_another_admin,
         match_room,
         match_room_1_deleted,
         instant_room,
         instant_room_1_deleted) = rooms

        another_admin = await database_sync_to_async(User.objects.create_superuser)(
            email=f'admin_user1@example.com',
            phone='+79993332211',
            fullname='Админов Админ Админович',
            password='Pass!234',
            is_active=True
        )

        await support_room1.participants.aset([user1])
        await support_room2.participants.aset([user2])
        await own_support_room.participants.aset([self.admin_user])
        await support_another_admin.participants.aset([another_admin])
        await match_room.participants.aset([user1, user2])
        await match_room_1_deleted.participants.aset([user1])
        await instant_room.participants.aset([user1, user2])
        await instant_room_1_deleted.participants.aset([user1])

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.get_rooms(communicator, 1)

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        results = response['data']['results']

        self.assertEqual(len(results), len(rooms))  # admins get all rooms

        support_room1_response = list(filter(lambda obj: obj['id'] == support_room1.id, results))
        support_room2_response = list(filter(lambda obj: obj['id'] == support_room2.id, results))
        own_support_room_response = list(filter(lambda obj: obj['id'] == own_support_room.id, results))
        support_another_admin_response = list(
            filter(lambda obj: obj['id'] == support_another_admin.id, results)
        )
        match_room_response = list(filter(lambda obj: obj['id'] == match_room.id, results))
        match_room_1_deleted_response = list(filter(lambda obj: obj['id'] == match_room_1_deleted.id, results))
        instant_room_response = list(filter(lambda obj: obj['id'] == instant_room.id, results))
        instant_room_1_deleted_response = list(
            filter(lambda obj: obj['id'] == instant_room_1_deleted.id, results)
        )

        # check number of interlocutors in rooms
        # check support rooms of users
        self.assertEqual(len(support_room1_response[0]['interlocutors']), 1)
        self.assertEqual(len(support_room2_response[0]['interlocutors']), 1)

        # check own support room
        self.assertEqual(len(own_support_room_response[0]['interlocutors']), 0)  # change to W2W agency

        # check support room of another admin
        self.assertEqual(len(support_another_admin_response[0]['interlocutors']), 1)
        self.assertEqual(support_another_admin_response[0]['interlocutors'][0]['id'], another_admin.id)

        # check match room
        self.assertEqual(len(match_room_response[0]['interlocutors']), 2)

        # check match room with 1 deleted user
        self.assertEqual(len(match_room_1_deleted_response[0]['interlocutors']), 1)

        # check instant room
        self.assertEqual(len(instant_room_response[0]['interlocutors']), 2)

        # check instant room with 1 deleted user
        self.assertEqual(len(instant_room_1_deleted_response[0]['interlocutors']), 1)

    async def test_get_rooms_pagination(self):
        rooms = await Room.objects.abulk_create([
            Room(type=Room.SUPPORT)
            for _ in range(120)
        ])

        message1 = await Message.objects.acreate(
            text='afasf',
            user=self.admin_user,
            room=rooms[10]
        )

        message2 = await Message.objects.acreate(
            text='afasf',
            user=self.admin_user,
            room=rooms[11]
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
