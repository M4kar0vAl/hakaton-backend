import factory
from django.test import TestCase, override_settings

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.factories import SubscriptionFactory
from core.apps.payments.models import Subscription
from core.apps.payments.tasks import deactivate_expired_subscriptions


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPOGATES=True
)
class DeactivateExpiredSubscriptionsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.brand = BrandShortFactory(user=cls.user)

        subscriptions = SubscriptionFactory.create_batch(
            2, brand=cls.brand, expired=factory.Iterator([False, True])
        )
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
