from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.factories import TariffFactory, PromoCodeFactory, SubscriptionFactory, GiftPromoCodeFactory


class GiftPromoCodeCreateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)
        cls.brand = BrandShortFactory(user=cls.user)

        cls.trial_tariff = TariffFactory(trial=True)
        cls.lite_tariff = TariffFactory(lite=True)
        cls.business_tariff = TariffFactory(business=True)

        cls.active_sub = SubscriptionFactory(brand=cls.brand, tariff=cls.business_tariff)
        cls.promocode = PromoCodeFactory()

        cls.url = reverse('gift_promocodes-list')

    def test_create_gift_promocode_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'tariff': self.lite_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_gift_promocode_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.post(self.url, {'tariff': self.lite_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_gift_promocode_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.post(self.url, {'tariff': self.lite_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_gift_promocode_cannot_gift_trial(self):
        response = self.auth_client.post(self.url, {'tariff': self.trial_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_gift_promocode_for_lite_tariff(self):
        response = self.auth_client.post(self.url, {'tariff': self.lite_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['promocode'])

    def test_create_gift_promocode_for_business_tariff(self):
        response = self.auth_client.post(self.url, {'tariff': self.business_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['promocode'])

    def test_create_gift_promocode_with_promocode(self):
        response = self.auth_client.post(self.url, {'tariff': self.lite_tariff.id, 'promocode': self.promocode.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['promocode'], self.promocode.id)

    def test_create_gift_promocode_if_promocode_already_used_in_gift(self):
        GiftPromoCodeFactory(giver=self.brand, promocode=self.promocode)
        response = self.auth_client.post(self.url, {'tariff': self.lite_tariff.id, 'promocode': self.promocode.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_gift_promocode_if_promocode_already_used_in_subscription(self):
        self.active_sub.promocode = self.promocode
        self.active_sub.save()

        response = self.auth_client.post(self.url, {
            'tariff': self.lite_tariff.id,
            'promocode': self.promocode.id  # try to use the same promo code
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
