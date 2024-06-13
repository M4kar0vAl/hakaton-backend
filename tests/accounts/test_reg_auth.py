from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient

from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class BoardTestCase(APITestCase):
    def setUp(self):
        user_data = {
            'email': 'user1@example.com',
            'phone': '+79993332211',
            'password': 'Pass!234',
            'is_active': True,
        }
        self.user = User.objects.create_user(**user_data)
        self.client = APIClient()
        self.auth_client = APIClient()
        self.auth_client.force_authenticate(self.user)

    def test_create_user(self):
        data = {
            'email': 'test@mail.com',
            'phone': '+79087917702',
            'password': 'Pass!234'
        }
        response = self.client.post(reverse('users-list'), data)
        self.assertEqual(201, response.status_code)
        self.assertEqual(2, len(User.objects.all()))

    def test_bad_mail_create_user(self):
        data = {
            'email': 'testmail.com',
            'phone': '+79087917702',
            'password': 'Pass!234'
        }
        response = self.client.post(reverse('users-list'), data)
        self.assertEqual(400, response.status_code)
        self.assertEqual(1, len(User.objects.all()))

    def test_bad_pass_create_user(self):
        data = {
            'email': 'test@mail.com',
            'phone': '+79993332211',
            'password': '1234'
        }
        response = self.client.post(reverse('users-list'), data)
        self.assertEqual(400, response.status_code)
        self.assertEqual(1, len(User.objects.all()))

    def test_bad_phone_create_user(self):
        data = {
            'email': 'test@mail.com',
            'phone': '+7999333',
            'password': 'Pass!234'
        }
        response = self.client.post(reverse('users-list'), data)
        self.assertEqual(400, response.status_code)
        self.assertEqual(1, len(User.objects.all()))

    def test_not_unique_mail_create_user(self):
        data = {
            'email': 'user1@example.com',
            'phone': '+79087917702',
            'password': 'Pass!234'
        }
        response = self.client.post(reverse('users-list'), data)
        self.assertEqual(400, response.status_code)
        self.assertEqual(1, len(User.objects.all()))

    def test_login_user(self):
        data = {
            'email': 'user1@example.com',
            'password': 'Pass!234'
        }
        response = self.client.post(reverse('jwt_create'), data)
        self.assertEqual(200, response.status_code)

    def test_login_bad_email(self):
        data = {
            'email': 'user@example.com',
            'password': 'Pass!234'
        }
        response = self.client.post(reverse('jwt_create'), data)
        self.assertEqual(401, response.status_code)

    def test_login_bad_pass(self):
        data = {
            'email': 'user1@example.com',
            'password': 'Pass!2345'
        }
        response = self.client.post(reverse('jwt_create'), data)
        self.assertEqual(401, response.status_code)

    def test_get_user(self):
        access = AccessToken.for_user(self.user)
        response = self.auth_client.get(
            reverse('users-me'),
            headers={'Authorization': f'Bearer {access}'}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(self.user.id, response.json()['id'])

    def test_patch_user(self):
        data = {
            'phone': '+79998887766',
        }
        response = self.auth_client.patch(reverse('users-me'), data)
        self.assertEqual(200, response.status_code)
        self.assertEqual('+79998887766', self.user.phone)

    def test_patch_bad_phone(self):
        data = {
            'phone': '+7999888776611',
        }
        response = self.auth_client.patch(reverse('users-me'), data)
        self.assertEqual(400, response.status_code)

    def test_delete_user(self):
        response = self.auth_client.delete(reverse('users-me'))
        self.assertEqual(204, response.status_code)

    def test_pass_reset(self):
        data = {
            'password': 'HardP@$$'
        }
        response = self.auth_client.post(reverse('users-password_reset'), data)
        self.assertEqual(200, response.status_code)
        self.user.check_password('HardP@$$')

    def test_pass_reset_bad_pass(self):
        data = {
            'password': 'simple'
        }
        response = self.auth_client.post(reverse('users-password_reset'), data)
        self.assertEqual(400, response.status_code)
