from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings, tag
from django.utils import timezone

from core.apps.brand.models import Category, Brand
from core.apps.chat.consumers import RoomConsumer
from core.apps.payments.models import Tariff, Subscription
from tests.utils import get_websocket_communicator, get_websocket_communicator_for_user

User = get_user_model()


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

    # used to reload data from migrations in TransactionTestCase
    # https://docs.djangoproject.com/en/5.0/topics/testing/overview/#rollback-emulation
    serialized_rollback = True

    # TransactionTestCase does not support setUpTestData method
    def setUp(self):
        self.user = User.objects.create_user(
            email=f'user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        country = Country.objects.create(name='Country', continent='EU')
        city = City.objects.create(name='City', country=country)

        self.brand_data = {
            'tg_nickname': '@asfhbnaf',
            'city': city,
            'name': 'brand1',
            'position': 'position',
            'category': Category.objects.get(id=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        self.brand = Brand.objects.create(user=self.user, **self.brand_data)

        now = timezone.now()
        tariff = Tariff.objects.get(name='Lite Match')
        tariff_relativedelta = tariff.get_duration_as_relativedelta()

        Subscription.objects.create(
            brand=self.brand,
            tariff=tariff,
            start_date=now,
            end_date=now + tariff_relativedelta,
            is_active=True
        )

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
        user_wo_brand = await User.objects.acreate(
            email=f'user_wo_brand@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=user_wo_brand
        )

        connected, _ = await communicator.connect()

        self.assertFalse(connected)

        # check that scope was populated with user
        # but connection rejected because user has no brand
        self.assertEqual(communicator.scope['user'].id, user_wo_brand.id)

        await communicator.disconnect()

    async def test_connect_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await User.objects.acreate(
            email=f'user_wo_active_sub@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        await Brand.objects.acreate(user=user_wo_active_sub, **self.brand_data)

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=user_wo_active_sub
        )

        connected, _ = await communicator.connect()

        self.assertFalse(connected)

        self.assertEqual(communicator.scope['user'].id, user_wo_active_sub.id)

        await communicator.disconnect()

    async def test_connect_authenticated_brand(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user
        )

        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)
        self.assertEqual(subprotocol, self.accepted_protocol)

        # check that scope was populated with user
        self.assertEqual(communicator.scope['user'].id, self.user.id)

        await communicator.disconnect()

    async def test_connect_unsupported_protocol(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=['unsupported'],
            user=self.user
        )

        connected, _ = await communicator.connect()

        self.assertFalse(connected)

        self.assertEqual(communicator.scope['subprotocols'], ['unsupported'])

        await communicator.disconnect()

    async def test_connect_supported_and_unsupported_protocols_together(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=['unsupported', self.accepted_protocol],
            user=self.user
        )

        connected, subprotocol = await communicator.connect()

        self.assertTrue(connected)
        self.assertEqual(subprotocol, self.accepted_protocol)

        await communicator.disconnect()
