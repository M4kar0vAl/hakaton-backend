from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from tests.factories import APIClientFactory

User = get_user_model()


class UserUpdateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClientFactory(user=cls.user)

        cls.update_data = {
            'phone': '+71111111111',
            'fullname': 'John Doe'
        }

        cls.url = reverse('users-me')

    def test_user_update_unauthenticated_not_allowed(self):
        response = self.client.patch(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_update(self):
        response = self.auth_client.patch(self.url, self.update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = User.objects.get(pk=self.user.pk)

        self.assertEqual(user.phone, self.update_data['phone'])
        self.assertEqual(user.fullname, self.update_data['fullname'])

    def test_user_update_bad_phone(self):
        response = self.auth_client.patch(self.url, {**self.update_data, 'phone': '+71928'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(pk=self.user.pk)

        self.assertEqual(user.phone, self.user.phone)  # check that phone wasn't changed

    def test_user_update_bad_fullname(self):
        response = self.auth_client.patch(self.url, {
            **self.update_data,
            'fullname': 's' * 513  # more than max length
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(pk=self.user.pk)

        self.assertEqual(user.fullname, self.user.fullname)  # check that fullname wasn't changed
