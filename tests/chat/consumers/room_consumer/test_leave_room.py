import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.chat.factories import RoomAsyncFactory
from core.apps.payments.factories import SubscriptionFactory, SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import join_room_communal, join_room, get_user_communicator, websocket_connect


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

        async with join_room(communicator, room.pk, connect=True):
            # make sub inactive
            sub.is_active = False
            await sub.asave()

            response = await self.leave_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

    async def test_leave_room(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])

        communicator1 = get_user_communicator(self.user1)
        communicator2 = get_user_communicator(self.user2)

        async with join_room_communal([communicator1, communicator2], room.pk, connect=True):
            response = await self.leave_room(communicator1)
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to the second user

        self.assertEqual(response['response_status'], status.HTTP_200_OK)
        self.assertEqual(response['data']['response'], f'Leaved room {room.pk} successfully!')

    async def test_leave_room_if_not_in_room(self):
        await RoomAsyncFactory(participants=[self.user1])

        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            response = await self.leave_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
