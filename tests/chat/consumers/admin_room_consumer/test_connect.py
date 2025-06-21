from django.test import override_settings, TransactionTestCase, tag

from core.apps.accounts.factories import UserAsyncFactory, UserFactory
from core.apps.chat.consumers import AdminRoomConsumer
from tests.utils import get_websocket_communicator, get_websocket_communicator_for_user


# IMPORTANT
# won't work with redis for some reason (in tests only)
@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerConnectTestCase(TransactionTestCase):
    # IMPORTANT
    # won't work if inherit from TestCase
    # having troubles with db connection maintenance (closed before middleware can authenticate user)

    # TransactionTestCase does not support setUpTestData method
    def setUp(self):
        self.admin_user = UserFactory(admin=True)

        self.path = 'ws/admin-chat/'
        self.accepted_protocol = 'admin-chat'

    async def test_unauthenticated_connect_not_allowed(self):
        communicator = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
        )

        connected, _ = await communicator.connect()
        self.assertFalse(connected)

        self.assertTrue(communicator.scope['user'].is_anonymous)

        await communicator.disconnect()

    async def test_connect_non_admin_user_not_allowed(self):
        non_admin_user = await UserAsyncFactory()

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=non_admin_user
        )

        connected, _ = await communicator.connect()
        self.assertFalse(connected)

        self.assertEqual(communicator.scope['user'].pk, non_admin_user.pk)

        await communicator.disconnect()

    async def test_connect_unsupported_protocol(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=['unsupported'],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertFalse(connected)

        self.assertEqual(communicator.scope['subprotocols'], ['unsupported'])

        await communicator.disconnect()

    async def test_connect_supported_and_unsupported_protocols_together(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=['unsupported', self.accepted_protocol],
            user=self.admin_user
        )

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        self.assertEqual(subprotocol, self.accepted_protocol)

        await communicator.disconnect()

    async def test_connect_admin_user(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        self.assertEqual(subprotocol, self.accepted_protocol)
        self.assertEqual(communicator.scope['user'].pk, self.admin_user.pk)

        await communicator.disconnect()
