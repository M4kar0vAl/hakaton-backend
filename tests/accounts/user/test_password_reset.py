from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from tests.factories import APIClientFactory

User = get_user_model()


class UserPasswordResetTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClientFactory(user=cls.user)

        cls.url = reverse('users-password_reset')

    def test_user_password_reset_unauthenticated_not_allowed(self):
        response = self.client.patch(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_password_reset(self):
        response = self.auth_client.post(self.url, {'password': 'HardP@$$'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_password_reset_bad_pass(self):
        response = self.auth_client.post(self.url, {'password': 'simple'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
