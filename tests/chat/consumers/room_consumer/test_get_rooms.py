import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.chat.factories import RoomAsyncFactory, MessageAsyncFactory
from core.apps.chat.models import Room
from core.apps.payments.factories import SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import get_user_communicator, websocket_connect


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    },
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
@tag('slow', 'chats')
class RoomConsumerGetRoomsTestCase(TransactionTestCase, RoomConsumerActionsMixin):

    def setUp(self):
        self.user1, self.user2 = UserFactory.create_batch(2)
        self.brand1, self.brand2 = BrandShortFactory.create_batch(
            2, user=factory.Iterator([self.user1, self.user2]), has_sub=True
        )

    async def test_get_rooms_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        await RoomAsyncFactory(participants=[user_wo_active_sub])
        sub = await SubscriptionAsyncFactory(brand__user=user_wo_active_sub)  # create active sub

        communicator = get_user_communicator(user_wo_active_sub)

        async with websocket_connect(communicator):
            # make sub inactive
            sub.is_active = False
            await sub.asave()

            response = await self.get_rooms(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_get_rooms(self):
        both_users = [self.user1, self.user2]
        rooms = await RoomAsyncFactory(
            5,
            type=factory.Iterator([Room.MATCH, Room.INSTANT, Room.SUPPORT]),
            participants=factory.Iterator([both_users, both_users, [self.user1], [self.user1], [self.user1]])
        )

        await MessageAsyncFactory(2, user=self.user1, room=factory.Iterator([rooms[0], rooms[1]]))
        await MessageAsyncFactory(user=self.user2, room=rooms[0])

        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            response = await self.get_rooms(communicator, 1)

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
        self.assertEqual(match_room_resp['last_message']['user'], self.user2.pk)

        # check interlocutors brands
        # check match room
        self.assertEqual(len(match_room_resp['interlocutors']), 1)
        self.assertEqual(match_room_resp['interlocutors'][0]['brand']['id'], self.brand2.pk)

        # check instant room
        self.assertEqual(len(instant_room_resp['interlocutors']), 1)
        self.assertEqual(instant_room_resp['interlocutors'][0]['brand']['id'], self.brand2.pk)

        # check support room
        self.assertEqual(len(support_room_resp['interlocutors']), 0)  # change to W2W agency

        # check match room with deleted interlocutor
        self.assertEqual(len(match_room_1_deleted_resp['interlocutors']), 0)

        # check instant room with deleted interlocutor
        self.assertEqual(len(instant_room_1_deleted_resp['interlocutors']), 0)

    async def test_get_rooms_does_not_return_rooms_of_other_brands(self):
        another_user = await UserAsyncFactory()

        both_users = [another_user, self.user2]
        await RoomAsyncFactory(
            3,
            type=factory.Iterator([Room.MATCH, Room.INSTANT, Room.SUPPORT]),
            participants=factory.Iterator([both_users, both_users, [another_user]])
        )

        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            response = await self.get_rooms(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)
        self.assertFalse(response['data']['results'])

    async def test_get_rooms_pagination(self):
        rooms = await RoomAsyncFactory(120, type=Room.MATCH, participants=[self.user1, self.user2])
        message1 = await MessageAsyncFactory(user=self.user1, room=rooms[10])
        message2 = await MessageAsyncFactory(user=self.user1, room=rooms[11])

        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
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
            self.assertEqual(results[0]['last_message']['id'], message2.pk)
            self.assertEqual(results[1]['last_message']['id'], message1.pk)

            # page 2
            response = await self.get_rooms(communicator, 2)
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            results = response['data']['results']
            next_ = response['data']['next']

            self.assertEqual(len(results), 20)
            self.assertIsNone(next_)

    async def test_get_rooms_last_message_includes_attachments(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])
        message = await MessageAsyncFactory(user=self.user1, room=room, has_attachments=True)
        attachments_ids = [pk async for pk in message.attachments.values_list('pk', flat=True).aiterator()]

        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            response = await self.get_rooms(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        results = response['data']['results']
        self.assertEqual(len(results), 1)

        last_message = results[0]['last_message']
        self.assertTrue('attachments' in last_message)

        response_attachments_ids = [a['id'] for a in last_message['attachments']]
        self.assertEqual(response_attachments_ids, attachments_ids)
