from django.test import TransactionTestCase, override_settings, tag

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.brand.factories import BrandShortAsyncFactory
from core.apps.chat.consumers import RoomConsumer
from core.apps.chat.utils import channels_reverse
from core.apps.payments.factories import SubscriptionFactory
from tests.utils import get_websocket_communicator, get_user_communicator, websocket_connect


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
class RoomConsumerConnectTestCase(TransactionTestCase):
    # IMPORTANT
    # won't work if inherit from TestCase
    # having troubles with db connection maintenance (closed before middleware can authenticate user)

    accepted_protocol = 'chat'

    # TransactionTestCase does not support setUpTestData method
    def setUp(self):
        self.user = UserFactory()

        SubscriptionFactory(brand__user=self.user)

    async def test_unauthenticated_connect_not_allowed(self):
        path = channels_reverse('chat')
        url_pattern = path.removeprefix('/')

        communicator = get_websocket_communicator(
            url_pattern=url_pattern,
            path=path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
        )

        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            self.assertFalse(is_connected)
            self.assertTrue(communicator.scope['user'].is_anonymous)

    async def test_connect_wo_brand(self):
        user_wo_brand = await UserAsyncFactory()

        communicator = get_user_communicator(user_wo_brand)

        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            self.assertFalse(is_connected)

            # check that scope was populated with user
            # but connection rejected because user has no brand
            self.assertEqual(communicator.scope['user'].pk, user_wo_brand.pk)

    async def test_connect_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        await BrandShortAsyncFactory(user=user_wo_active_sub)

        communicator = get_user_communicator(user_wo_active_sub)

        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            self.assertFalse(is_connected)
            self.assertEqual(communicator.scope['user'].pk, user_wo_active_sub.pk)

    async def test_connect_authenticated_brand(self):
        communicator = get_user_communicator(self.user)

        async with websocket_connect(communicator) as (_, subprotocol):
            self.assertEqual(subprotocol, self.accepted_protocol)

            # check that scope was populated with user
            self.assertEqual(communicator.scope['user'].pk, self.user.pk)

    async def test_connect_unsupported_protocol(self):
        communicator = get_user_communicator(self.user, protocols=['unsupported'])

        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            self.assertFalse(is_connected)
            self.assertEqual(communicator.scope['subprotocols'], ['unsupported'])

    async def test_connect_supported_and_unsupported_protocols_together(self):
        communicator = get_user_communicator(self.user, protocols=['unsupported', self.accepted_protocol])

        async with websocket_connect(communicator) as (_, subprotocol):
            self.assertEqual(subprotocol, self.accepted_protocol)
