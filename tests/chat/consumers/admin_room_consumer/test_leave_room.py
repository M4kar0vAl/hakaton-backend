from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import AdminUserFactory, UserAsyncFactory
from core.apps.chat.consumers import AdminRoomConsumer, RoomConsumer
from core.apps.chat.factories import RoomSupportAsyncFactory
from core.apps.payments.factories import SubscriptionAsyncFactory
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import get_websocket_communicator_for_user


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerLeaveRoomTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):
    serialized_rollback = True

    def setUp(self):
        self.admin_user = AdminUserFactory()

        self.path = 'ws/admin-chat/'
        self.accepted_protocol = 'admin-chat'

        self.user_path = 'ws/chat/'
        self.user_accepted_protocol = 'chat'

    async def test_leave_room_not_in_room(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.leave_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_leave_room(self):
        user = await UserAsyncFactory()
        room = await RoomSupportAsyncFactory(participants=[user])
        await SubscriptionAsyncFactory(brand__user=user)

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
