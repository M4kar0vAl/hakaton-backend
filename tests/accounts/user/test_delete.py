from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory

User = get_user_model()


class UserDeleteTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

        cls.url = reverse('users-me')

    def test_user_delete(self):
        response = self.auth_client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
