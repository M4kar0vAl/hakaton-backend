from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserCreateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.valid_data = {
            'email': 'test@mail.com',
            'phone': '+79087917702',
            'fullname': 'Юзеров Юзер Юзерович',
            'password': 'Pass!234'
        }

        cls.url = reverse('users-list')

    def test_user_create(self):
        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(User.objects.filter(pk=response.data['id']).exists())

    def test_user_create_bad_email(self):
        bad_mail = 'testmail.com'
        response = self.client.post(self.url, {**self.valid_data, 'email': bad_mail})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(User.objects.filter(email=bad_mail).exists())

    def test_user_create_bad_pass(self):
        response = self.client.post(self.url, {**self.valid_data, 'password': 1234
                                               })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(User.objects.filter(email=self.valid_data['email']).exists())

    def test_user_create_bad_phone(self):
        bad_phone = '+7999333'
        response = self.client.post(self.url, {**self.valid_data, 'phone': bad_phone})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(User.objects.filter(email=self.valid_data['email'], phone=bad_phone).exists())

    def test_user_create_email_is_not_unique(self):
        existing_user = User.objects.create_user(**self.valid_data)

        # uses the same email
        response = self.client.post(self.url, {
            'email': existing_user.email,
            'phone': '+71111111111',
            'fullname': 'Юзеров1 Юзер1 Юзерович1',
            'password': 'Pass!@34'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(User.objects.filter(email=existing_user.email).count(), 1)
