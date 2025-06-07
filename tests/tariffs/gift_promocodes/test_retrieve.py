from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.factories import GiftPromoCodeFactory


class GiftPromoCodeRetrieveTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)
        cls.brand = BrandShortFactory(user=cls.user)

        cls.valid_gift = GiftPromoCodeFactory(giver=cls.brand)
        cls.used_gift = GiftPromoCodeFactory(giver=cls.brand, is_used=True)
        cls.expired_gift = GiftPromoCodeFactory(giver=cls.brand, expired=True)

        cls.valid_gift_url = reverse('gift_promocodes-detail', args=[cls.valid_gift.code])
        cls.used_gift_url = reverse('gift_promocodes-detail', args=[cls.used_gift.code])
        cls.expired_gift_url = reverse('gift_promocodes-detail', args=[cls.expired_gift.code])

    def test_retrieve_gift_promocode_unauthenticated_now_allowed(self):
        response = self.client.get(self.valid_gift_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_gift_promocode_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.get(self.valid_gift_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_gift_promocode_already_used(self):
        response = self.auth_client.get(self.used_gift_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_gift_promocode_expired(self):
        response = self.auth_client.get(self.expired_gift_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_gift_promocode(self):
        response = self.auth_client.get(self.valid_gift_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.valid_gift.id)

    def test_retrieve_gift_promocode_by_another_brand(self):
        another_user = UserFactory()
        another_auth_client = APIClient()
        another_auth_client.force_authenticate(another_user)

        BrandShortFactory(user=another_user)

        response = another_auth_client.get(self.valid_gift_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
