import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.factories import TariffFactory, SubscriptionFactory
from tests.factories import APIClientFactory


class TariffUpgradeTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2, cls.user3 = UserFactory.create_batch(3)
        cls.auth_client1, cls.auth_client2, cls.auth_client3 = APIClientFactory.create_batch(
            3, user=factory.Iterator([cls.user1, cls.user2, cls.user3])
        )

        cls.trial_brand, cls.lite_brand, cls.business_brand = BrandShortFactory.create_batch(
            3, user=factory.Iterator([cls.user1, cls.user2, cls.user3])
        )

        cls.trial = TariffFactory(trial=True)
        cls.lite = TariffFactory(lite=True)
        cls.business = TariffFactory(business=True)

        SubscriptionFactory.create_batch(
            3,
            brand=factory.Iterator([cls.trial_brand, cls.lite_brand, cls.business_brand]),
            tariff=factory.Iterator([cls.trial, cls.lite, cls.business])
        )

        cls.url = reverse('tariffs-upgrade')

    def test_tariff_upgrade_unauthenticated_not_allowed(self):
        response = self.client.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tariff_upgrade_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClientFactory(user=user_wo_brand)

        response = auth_client_wo_brand.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tariff_upgrade_wo_active_unexpired_sub_not_allowed(self):
        user = UserFactory()
        auth_client_wo_sub = APIClientFactory(user=user)

        BrandShortFactory(user=user)

        response = auth_client_wo_sub.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tariff_upgrade_for_brand_on_trial_not_allowed(self):
        response = self.auth_client1.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tariff_upgrade_for_brand_on_business_not_allowed(self):
        response = self.auth_client3.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tariff_upgrade(self):
        response = self.auth_client2.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that another subscription wasn't created
        self.assertEqual(self.lite_brand.subscriptions.count(), 1)

        current_sub = self.lite_brand.get_active_subscription()

        self.assertEqual(current_sub.tariff_id, self.business.id)  # check that upgraded to business
        self.assertEqual(current_sub.upgraded_from_id, self.lite.id)  # check that upgraded from lite
        self.assertIsNotNone(current_sub.upgraded_at)  # check that upgraded timestamp is not None

    def test_tariff_upgrade_cannot_upgrade_to_trial(self):
        response = self.auth_client2.patch(self.url, {'tariff': self.trial.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tariff_upgrade_cannot_upgrade_to_lite(self):
        response = self.auth_client2.patch(self.url, {'tariff': self.lite.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
