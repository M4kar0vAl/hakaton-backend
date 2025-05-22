from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory

User = get_user_model()


class UserLoginTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        password = 'Pass!234'
        cls.user = UserFactory(password=password)

        cls.login_data = {
            'email': cls.user.email,
            'password': password
        }

        cls.url = reverse('jwt_create')

    def test_user_login(self):
        response = self.client.post(self.url, self.login_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_login_not_existing_email(self):
        response = self.client.post(self.url, {
            **self.login_data,
            'email': 'user@example.com'
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_login_bad_email(self):
        response = self.client.post(self.url, {
            **self.login_data,
            'email': 'user_example.com'
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_login_bad_pass(self):
        response = self.client.post(self.url, {
            **self.login_data,
            'password': 'notMyPass!2345'
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
