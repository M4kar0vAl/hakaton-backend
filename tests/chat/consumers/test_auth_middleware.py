from datetime import timedelta

from channels.testing import WebsocketCommunicator
from django.test import override_settings, TransactionTestCase, tag
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from core.apps.accounts.factories import UserFactory
from core.apps.chat.consumers import RoomConsumer
from core.apps.chat.utils import channels_reverse
from core.apps.payments.factories import SubscriptionFactory
from tests.utils import get_websocket_communicator, get_websocket_application, get_user_communicator, websocket_connect


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
class AuthMiddlewareTestCase(TransactionTestCase):
    # IMPORTANT
    # won't work if inherit from TestCase
    # having troubles with db connection maintenance (closed before middleware can authenticate user)

    # TransactionTestCase does not support setUpTestData method
    def setUp(self):
        self.user = UserFactory()
        SubscriptionFactory(brand__user=self.user)  # need this to connect to RoomConsumer

        self.path = channels_reverse('chat')
        self.url_pattern = self.path.removeprefix('/')
        self.accepted_protocol = 'chat'

    async def test_connect_token_not_last_in_protocol_list(self):
        access = AccessToken.for_user(self.user)

        # middleware is the same for both RoomConsumer and AdminRoomConsumer,
        # so it doesn't matter which to use in tests
        app = get_websocket_application(
            url_pattern=self.url_pattern,
            consumer_class=RoomConsumer
        )

        protocols = f'{access}, {self.accepted_protocol}'

        communicator = WebsocketCommunicator(
            app,
            path=self.path,
            headers=[
                (b'sec-websocket-protocol', bytes(protocols, 'utf-8'))
            ],
            subprotocols=protocols.split(', ')
        )

        # middleware transforms request after communicator.connect()
        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            self.assertFalse(is_connected)

        scope = communicator.scope

        self.assertTrue(scope['user'].is_anonymous)

        # check that token wasn't removed from subprotocols and headers
        # token IS NOT a valid subprotocol
        self.assertEqual(scope['subprotocols'][0], str(access))
        self.assertEqual(
            dict(scope['headers'])[b'sec-websocket-protocol'],
            bytes(str(access), 'utf-8')
        )

    async def test_connect_expired_token(self):
        access = AccessToken.for_user(self.user)
        access.set_exp(
            from_time=timezone.now() - timedelta(days=1),
            lifetime=timedelta(minutes=30)
        )

        communicator = get_websocket_communicator(
            url_pattern=self.url_pattern,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            token=access
        )

        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            self.assertFalse(is_connected)

        # if token is expired, then middleware populates scope with AnonymousUser
        self.assertTrue(communicator.scope['user'].is_anonymous)

    async def test_connect_protocols_not_specified_except_token(self):
        communicator = get_user_communicator(self.user, protocols=[])

        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            # connection will be rejected, because accepted protocol not in the subprotocols list
            self.assertFalse(is_connected)

        scope = communicator.scope

        # token will be correctly transformed to user
        self.assertFalse(scope['user'].is_anonymous)

        # because token is the only "protocol", then it will be removed,
        # so headers and subprotocols will be empty
        self.assertFalse(scope['headers'])
        self.assertFalse(scope['subprotocols'])

    async def test_connect_header_not_specified(self):
        access = AccessToken.for_user(self.user)

        app = get_websocket_application(
            url_pattern=self.url_pattern,
            consumer_class=RoomConsumer
        )

        protocols = f'{self.accepted_protocol}, {access}'

        communicator = WebsocketCommunicator(
            app,
            path=self.path,
            subprotocols=protocols.split(', ')
        )

        async with websocket_connect(communicator, check_connected=False) as (is_connected, _):
            self.assertFalse(is_connected)

        scope = communicator.scope
        self.assertTrue(scope['user'].is_anonymous)
        self.assertFalse(scope['headers'])  # check that headers are empty

        # check that subprotocols were transformed correctly
        self.assertEqual(scope['subprotocols'], [self.accepted_protocol])

    async def test_connect(self):
        communicator = get_user_communicator(self.user)

        async with websocket_connect(communicator):
            self.assertEqual(communicator.scope['user'].pk, self.user.pk)
