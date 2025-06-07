from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.factories import PromoCodeFactory, SubscriptionFactory, TariffFactory


class TariffSubscribeTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)
        cls.brand = BrandShortFactory(user=cls.user)

        cls.trial_tariff_id = TariffFactory(trial=True).pk
        cls.lite_tariff_id = TariffFactory(lite=True).pk
        cls.business_tariff_id = TariffFactory(business=True).pk

        cls.promocode = PromoCodeFactory()

        cls.url = reverse('tariffs-subscribe')

    def test_tariff_subscribe_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'tariff': self.lite_tariff_id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tariff_subscribe_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.post(self.url, {'tariff': self.lite_tariff_id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tariff_subscribe_with_active_unexpired_subscription_not_allowed(self):
        SubscriptionFactory(brand=self.brand)
        response = self.auth_client.post(self.url, {'tariff': self.business_tariff_id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tariff_subscribe(self):
        response = self.auth_client.post(self.url, {'tariff': self.lite_tariff_id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.user.brand.subscriptions.count(), 1)

        subscription = self.user.brand.get_active_subscription()

        self.assertEqual(response.data['id'], subscription.id)
        self.assertIsNone(response.data['promocode'])

    def test_tariff_subscribe_with_promocode(self):
        response = self.auth_client.post(self.url, {'tariff': self.lite_tariff_id, 'promocode': self.promocode.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.user.brand.subscriptions.count(), 1)
        self.assertEqual(response.data['promocode'], self.promocode.id)

    def test_tariff_subscribe_with_expired_promocode(self):
        """
        Should be ok when creating with expired promo code, because promo code is checked before payment.
        After payment subscribe api is called with promo code that was used in payment.
        Promo code can expire between check for validity and calling subscribe api.
        That's why it shouldn't be validated in subscribe action.

        flow:
            apply promo -> check for validity -> return promo code if everything is ok -> create payment link -> pay ->
            call subscribe api (no need to check validity here, because user has already paid) -> return subscription
        """
        expired_promocode = PromoCodeFactory(expired=True)

        response = self.auth_client.post(self.url, {'tariff': self.lite_tariff_id, 'promocode': expired_promocode.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.user.brand.subscriptions.count(), 1)
        self.assertEqual(response.data['promocode'], expired_promocode.id)

    def test_tariff_subscribe_trial_ignores_promocode(self):
        response = self.auth_client.post(self.url, {'tariff': self.trial_tariff_id, 'promocode': self.promocode.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.user.brand.subscriptions.count(), 1)
        self.assertIsNone(response.data['promocode'])

    def test_tariff_subscribe_deactivates_active_tariffs(self):
        SubscriptionFactory(brand=self.brand, expired=True)  # brand has expired subscription

        response = self.auth_client.post(self.url, {'tariff': self.business_tariff_id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.brand.subscriptions.filter(is_active=True).count(), 1)
        self.assertEqual(self.brand.subscriptions.get(is_active=True).tariff.id, 3)
