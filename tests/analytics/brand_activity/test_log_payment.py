from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.analytics.models import BrandActivity
from core.apps.brand.factories import BrandShortFactory
from tests.factories import APIClientFactory


class LogPaymentTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClientFactory(user=cls.user)
        cls.brand = BrandShortFactory(user=cls.user)

        cls.url = reverse('analytics-log_payment')

    def test_log_payment_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_log_payment_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        client_wo_brand = APIClientFactory(user=user_wo_brand)

        response = client_wo_brand.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_log_payment(self):
        response = self.auth_client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check that instance was created in db
        self.assertTrue(BrandActivity.objects.filter(id=response.data['id']).exists())
