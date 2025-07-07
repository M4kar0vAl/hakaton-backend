from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.factories import PromoCodeFactory, SubscriptionFactory, GiftPromoCodeFactory
from tests.factories import APIClientFactory


class PromoCodeRetrieveTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClientFactory(user=cls.user)
        cls.brand = BrandShortFactory(user=cls.user)
        cls.promocode = PromoCodeFactory()

        cls.url = reverse('promocode-detail', args=[cls.promocode.code])

    def test_check_promocode_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_check_promocode_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClientFactory(user=user_wo_brand)

        response = auth_client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_promocode(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_promocode_does_not_exist(self):
        response = self.auth_client.get(reverse('promocode-detail', args=['not_existing']))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_promocode_already_used_in_subscription(self):
        SubscriptionFactory(brand=self.brand, promocode=self.promocode)

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_promocode_already_used_in_gift(self):
        GiftPromoCodeFactory(giver=self.brand, promocode=self.promocode)

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
