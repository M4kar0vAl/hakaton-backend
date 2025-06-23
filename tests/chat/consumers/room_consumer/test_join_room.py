import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.chat.factories import RoomAsyncFactory
from core.apps.chat.models import Room
from core.apps.payments.factories import SubscriptionFactory, SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import join_room, get_user_communicator


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
        self.user1, self.user2 = UserFactory.create_batch(2)
        self.brand1, self.brand2 = BrandShortFactory.create_batch(2, user=factory.Iterator([self.user1, self.user2]))

        SubscriptionFactory.create_batch(2, brand=factory.Iterator([self.brand1, self.brand2]))

    async def test_join_room_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        room = await RoomAsyncFactory(participants=[user_wo_active_sub])
        sub = await SubscriptionAsyncFactory(brand__user=user_wo_active_sub)  # create active sub

        communicator = get_user_communicator(user_wo_active_sub)

        # connect with active sub
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # make sub inactive
        sub.is_active = False
        await sub.asave()

        response = await self.join_room(communicator, room.pk)
        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_join_room(self):
        both_users = [self.user1, self.user2]
        rooms = await RoomAsyncFactory(
            3,
            type=factory.Iterator([Room.MATCH, Room.INSTANT, Room.SUPPORT]),
            participants=factory.Iterator([both_users, both_users, [self.user1]])
        )

        match_room, instant_room, support_room = rooms

        communicator = get_user_communicator(self.user1)

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # check join match room
        async with join_room(communicator, match_room.pk) as response:
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

        # check join instant room
        async with join_room(communicator, instant_room.pk) as response:
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

        # check join support room
        async with join_room(communicator, support_room.pk) as response:
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

        await communicator.disconnect()

    async def test_join_room_if_already_joined_another_one(self):
        room1, room2 = await RoomAsyncFactory(2, type=Room.MATCH, participants=[self.user1, self.user2])

        communicator = get_user_communicator(self.user1)

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room1.pk):
            # join room2
            response = await self.join_room(communicator, room2.pk)

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_join_the_same_room(self):
        room = await RoomAsyncFactory(participants=[self.user1])

        communicator = get_user_communicator(self.user1)

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            # try to rejoin room
            response = await self.join_room(communicator, room.pk)

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_join_room_not_a_member_of(self):
        room = await RoomAsyncFactory()

        communicator = get_user_communicator(self.user1)

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.join_room(communicator, room.pk)
        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])
