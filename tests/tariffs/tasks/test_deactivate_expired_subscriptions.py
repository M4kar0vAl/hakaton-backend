from datetime import timedelta

from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from core.apps.brand.models import Brand, Category
from core.apps.payments.models import Tariff, Subscription
from core.apps.payments.tasks import deactivate_expired_subscriptions

User = get_user_model()


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPOGATES=True
)
class DeactivateExpiredSubscriptionsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email=f'user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        country = Country.objects.create(name='Country', continent='EU')
        city = City.objects.create(name='City', country=country)

        brand_data = {
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

        cls.brand = Brand.objects.create(user=cls.user, **brand_data)

        tariff = Tariff.objects.get(id=2)
        tariff_relativedelta = tariff.get_duration_as_relativedelta()
        now = timezone.now()

        subscriptions = Subscription.objects.bulk_create([
            Subscription(
                brand=cls.brand,
                tariff=tariff,
                end_date=now + tariff_relativedelta,
                is_active=True,
            ),
            Subscription(
                brand=cls.brand,
                tariff=tariff,
                end_date=now - timedelta(minutes=1),
                is_active=True,
            ),
        ])

        cls.active_sub_id, cls.active_expired_sub_id = map(lambda x: x.id, subscriptions)

        cls.task = deactivate_expired_subscriptions

    def test_deactivate_expired_subscriptions(self):
        self.task.delay()

        # check that unexpired subscription wasn't deactivated
        self.assertTrue(
            Subscription.objects.filter(id=self.active_sub_id, is_active=True).exists()
        )

        # check that expired subscription was deactivated
        self.assertFalse(
            Subscription.objects.filter(id=self.active_expired_sub_id, is_active=True).exists()
        )
