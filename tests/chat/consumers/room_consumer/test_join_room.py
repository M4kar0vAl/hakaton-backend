import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.chat.factories import RoomAsyncFactory
from core.apps.chat.models import Room
from core.apps.payments.factories import SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import join_room, get_user_communicator, websocket_connect


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class RoomConsumerJoinRoomTestCase(TransactionTestCase, RoomConsumerActionsMixin):

    def setUp(self):
        self.user1, self.user2 = UserFactory.create_batch(2, has_sub=True)

    async def test_join_room_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        room = await RoomAsyncFactory(participants=[user_wo_active_sub])
        sub = await SubscriptionAsyncFactory(brand__user=user_wo_active_sub)  # create active sub

        communicator = get_user_communicator(user_wo_active_sub)

        # connect with active sub
        async with websocket_connect(communicator):
            # make sub inactive
            sub.is_active = False
            await sub.asave()

            response = await self.join_room(communicator, room.pk)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_join_room(self):
        both_users = [self.user1, self.user2]
        match_room, instant_room, support_room = await RoomAsyncFactory(
            3,
            type=factory.Iterator([Room.MATCH, Room.INSTANT, Room.SUPPORT]),
            participants=factory.Iterator([both_users, both_users, [self.user1]])
        )

        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            # check join match room
            async with join_room(communicator, match_room.pk) as response:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            # check join instant room
            async with join_room(communicator, instant_room.pk) as response:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            # check join support room
            async with join_room(communicator, support_room.pk) as response:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

    async def test_join_room_if_already_joined_another_one(self):
        room1, room2 = await RoomAsyncFactory(2, type=Room.MATCH, participants=[self.user1, self.user2])

        communicator = get_user_communicator(self.user1)

        async with join_room(communicator, room1.pk, connect=True):
            response = await self.join_room(communicator, room2.pk)  # try to join room2

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_join_the_same_room(self):
        room = await RoomAsyncFactory(participants=[self.user1])

        communicator = get_user_communicator(self.user1)

        async with join_room(communicator, room.pk, connect=True):
            # try to rejoin room
            response = await self.join_room(communicator, room.pk)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_join_room_not_a_member_of(self):
        room = await RoomAsyncFactory()

        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            response = await self.join_room(communicator, room.pk)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])
