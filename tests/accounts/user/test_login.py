from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserLoginTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_data = {
            'email': 'user1@example.com',
            'phone': '+79993332211',
            'fullname': 'Юзеров Юзер Юзерович',
            'password': 'Pass!234',
            'is_active': True
        }

        cls.user = User.objects.create_user(**cls.user_data)

        cls.login_data = {
            'email': cls.user_data['email'],
            'password': cls.user_data['password']
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
