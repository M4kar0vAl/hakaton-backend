from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserAsyncFactory, UserFactory
from core.apps.chat.factories import RoomAsyncFactory
from core.apps.chat.models import Room
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import get_admin_communicator, get_user_communicator, websocket_connect, join_room_communal


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

        async with websocket_connect(communicator):
            response = await self.leave_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_leave_room(self):
        user = await UserAsyncFactory(has_sub=True)
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[user])

        admin_communicator = get_admin_communicator(self.admin_user)
        user_communicator = get_user_communicator(user)

        async with join_room_communal([admin_communicator, user_communicator], room.pk, connect=True):
            response = await self.leave_room(admin_communicator)
            self.assertTrue(await user_communicator.receive_nothing())  # check that nothing was sent to the second user

        self.assertEqual(response['response_status'], status.HTTP_200_OK)
