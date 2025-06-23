from django.test import TransactionTestCase, override_settings, tag

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.brand.factories import BrandShortFactory, BrandShortAsyncFactory
from core.apps.chat.consumers import RoomConsumer
from core.apps.payments.factories import SubscriptionFactory
from tests.utils import get_websocket_communicator, get_user_communicator


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

    # TransactionTestCase does not support setUpTestData method
    def setUp(self):
        self.user = UserFactory()
        self.brand = BrandShortFactory(user=self.user)

        SubscriptionFactory(brand=self.brand)

        self.path = 'ws/chat/'
        self.accepted_protocol = 'chat'

    async def test_unauthenticated_connect_not_allowed(self):
        communicator = get_websocket_communicator(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
        )

        connected, _ = await communicator.connect()

        self.assertFalse(connected)
        self.assertTrue(communicator.scope['user'].is_anonymous)

        await communicator.disconnect()

    async def test_connect_wo_brand(self):
        user_wo_brand = await UserAsyncFactory()

        communicator = get_user_communicator(user_wo_brand)

        connected, _ = await communicator.connect()
        self.assertFalse(connected)

        # check that scope was populated with user
        # but connection rejected because user has no brand
        self.assertEqual(communicator.scope['user'].pk, user_wo_brand.pk)

        await communicator.disconnect()

    async def test_connect_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        await BrandShortAsyncFactory(user=user_wo_active_sub)

        communicator = get_user_communicator(user_wo_active_sub)
        connected, _ = await communicator.connect()

        self.assertFalse(connected)
        self.assertEqual(communicator.scope['user'].pk, user_wo_active_sub.pk)

        await communicator.disconnect()

    async def test_connect_authenticated_brand(self):
        communicator = get_user_communicator(self.user)
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)
        self.assertEqual(subprotocol, self.accepted_protocol)

        # check that scope was populated with user
        self.assertEqual(communicator.scope['user'].pk, self.user.pk)

        await communicator.disconnect()

    async def test_connect_unsupported_protocol(self):
        communicator = get_user_communicator(self.user, protocols=['unsupported'])
        connected, _ = await communicator.connect()

        self.assertFalse(connected)
        self.assertEqual(communicator.scope['subprotocols'], ['unsupported'])

        await communicator.disconnect()

    async def test_connect_supported_and_unsupported_protocols_together(self):
        communicator = get_user_communicator(self.user, protocols=['unsupported', self.accepted_protocol])
        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)
        self.assertEqual(subprotocol, self.accepted_protocol)

        await communicator.disconnect()
