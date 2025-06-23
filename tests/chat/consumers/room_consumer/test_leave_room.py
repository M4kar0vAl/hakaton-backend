import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.chat.factories import RoomAsyncFactory
from core.apps.payments.factories import SubscriptionFactory, SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import join_room_communal, join_room, get_user_communicator


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class RoomConsumerLeaveRoomTestCase(TransactionTestCase, RoomConsumerActionsMixin):

    def setUp(self):
        self.user1, self.user2 = UserFactory.create_batch(2)
        self.brand1, self.brand2 = BrandShortFactory.create_batch(2, user=factory.Iterator([self.user1, self.user2]))

        SubscriptionFactory.create_batch(2, brand=factory.Iterator([self.brand1, self.brand2]))

    async def test_leave_room_wo_active_sub_is_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        room = await RoomAsyncFactory(participants=[user_wo_active_sub])
        sub = await SubscriptionAsyncFactory(brand__user=user_wo_active_sub)  # create active sub

        communicator = get_user_communicator(user_wo_active_sub)

        # connect with active sub
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            # make sub inactive
            sub.is_active = False
            await sub.asave()

            response = await self.leave_room(communicator)
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

        await communicator.disconnect()

    async def test_leave_room(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])

        communicator1 = get_user_communicator(self.user1)
        communicator2 = get_user_communicator(self.user2)

        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        async with join_room_communal([communicator1, communicator2], room.pk):
            response = await self.leave_room(communicator1)
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to the second user

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            self.assertEqual(response['data']['response'], f'Leaved room {room.pk} successfully!')

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_leave_room_if_not_in_room(self):
        await RoomAsyncFactory(participants=[self.user1])

        communicator = get_user_communicator(self.user1)

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.leave_room(communicator)
        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
