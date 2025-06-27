from django.test import override_settings, TransactionTestCase, tag

from core.apps.accounts.factories import UserAsyncFactory, UserFactory
from core.apps.chat.consumers import AdminRoomConsumer
from core.apps.chat.utils import channels_reverse
from tests.utils import get_websocket_communicator, get_admin_communicator, websocket_connect


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

    accepted_protocol = 'admin-chat'

    # TransactionTestCase does not support setUpTestData method
    def setUp(self):
        self.admin_user = UserFactory(admin=True)

    async def test_unauthenticated_connect_not_allowed(self):
        path = channels_reverse('admin_chat')
        url_pattern = path.removeprefix('/')

        communicator = get_websocket_communicator(
            url_pattern=url_pattern,
            path=path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
        )

        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            self.assertFalse(is_connected)
            self.assertTrue(communicator.scope['user'].is_anonymous)

    async def test_connect_non_admin_user_not_allowed(self):
        non_admin_user = await UserAsyncFactory()

        communicator = get_admin_communicator(non_admin_user)

        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            self.assertFalse(is_connected)
            self.assertEqual(communicator.scope['user'].pk, non_admin_user.pk)

    async def test_connect_unsupported_protocol(self):
        communicator = get_admin_communicator(self.admin_user, protocols=['unsupported'])

        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            self.assertFalse(is_connected)
            self.assertEqual(communicator.scope['subprotocols'], ['unsupported'])

    async def test_connect_supported_and_unsupported_protocols_together(self):
        communicator = get_admin_communicator(self.admin_user, protocols=['unsupported', self.accepted_protocol])

        async with websocket_connect(communicator) as (is_connected, subprotocol):
            self.assertEqual(subprotocol, self.accepted_protocol)

    async def test_connect_admin_user(self):
        communicator = get_admin_communicator(self.admin_user)

        async with websocket_connect(communicator) as (is_connected, subprotocol):
            self.assertEqual(subprotocol, self.accepted_protocol)
            self.assertEqual(communicator.scope['user'].pk, self.admin_user.pk)
