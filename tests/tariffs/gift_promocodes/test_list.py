from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.factories import GiftPromoCodeFactory


class GiftPromoCodeListTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)
        cls.brand = BrandShortFactory(user=cls.user)

        GiftPromoCodeFactory(giver=cls.brand)  # valid
        GiftPromoCodeFactory(giver=cls.brand, is_used=True)  # used
        GiftPromoCodeFactory(giver=cls.brand, expired=True)  # expired

        cls.url = reverse('gift_promocodes-list')

    def test_list_gift_promocodes_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_gift_promocodes_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_gift_promocodes(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_gift_promocodes_excludes_already_used_gifts(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_gift_promocodes_excludes_expired_gifts(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_gift_promocodes_returns_only_current_brand_codes(self):
        GiftPromoCodeFactory()  # another brand's gift promocode

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
