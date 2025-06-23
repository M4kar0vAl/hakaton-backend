from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserAsyncFactory, UserFactory
from core.apps.chat.factories import RoomAsyncFactory
from core.apps.chat.models import Room
from core.apps.payments.factories import SubscriptionAsyncFactory
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import get_admin_communicator, get_user_communicator


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerLeaveRoomTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):

    def setUp(self):
        self.admin_user = UserFactory(admin=True)

    async def test_leave_room_not_in_room(self):
        communicator = get_admin_communicator(self.admin_user)

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.leave_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_leave_room(self):
        user = await UserAsyncFactory()
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[user])
        await SubscriptionAsyncFactory(brand__user=user)

        admin_communicator = get_admin_communicator(self.admin_user)
        user_communicator = get_user_communicator(user)

        admin_connected, _ = await admin_communicator.connect()
        user_connected, _ = await user_communicator.connect()

        self.assertTrue(admin_connected)
        self.assertTrue(user_connected)

        await self.join_room(admin_communicator, room.pk)
        await self.join_room(user_communicator, room.pk)

        response = await self.leave_room(admin_communicator)
        self.assertTrue(await user_communicator.receive_nothing())  # check that nothing was sent to the second user

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        await admin_communicator.disconnect()
        await user_communicator.disconnect()
