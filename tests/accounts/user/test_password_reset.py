from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

User = get_user_model()


class UserPasswordResetTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

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
