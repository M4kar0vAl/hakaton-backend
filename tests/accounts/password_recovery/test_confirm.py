from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.models import PasswordRecoveryToken
from core.apps.accounts.utils import get_recovery_token_hash

User = get_user_model()


class PasswordRecoveryConfirmTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.token = 'token'
        cls.non_existent_token = 'non_existent'
        cls.new_password = '#FHF*(8@)DJ'
        cls.invalid_new_password = '1234'

        cls.user = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.recovery_token = PasswordRecoveryToken.objects.create(
            token=get_recovery_token_hash(cls.token),
            user=cls.user
        )

        cls.url = reverse('password_recovery-confirm')

    def test_password_recovery_confirm_token_does_not_exist(self):
        response = self.client.post(self.url, {'token': self.non_existent_token, 'new_password': self.new_password})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check that password haven't changed
        self.assertFalse(self.user.check_password(self.new_password))

    def test_password_recovery_confirm_token_expired(self):
        # make token expired
        PasswordRecoveryToken.objects.filter(
            pk=self.recovery_token.pk
        ).update(
            created=F('created') - timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
        )

        response = self.client.post(self.url, {'token': self.token, 'new_password': self.new_password})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check that token remains in db
        self.assertTrue(PasswordRecoveryToken.objects.filter(pk=self.recovery_token.pk).exists())

        # check that password haven't changed
        self.assertFalse(self.user.check_password(self.new_password))

    def test_password_recovery_confirm_new_password_is_too_simple(self):
        response = self.client.post(self.url, {'token': self.token, 'new_password': self.invalid_new_password})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check that token remains in db
        self.assertTrue(PasswordRecoveryToken.objects.filter(pk=self.recovery_token.pk).exists())

        # check that password haven't changed
        self.assertFalse(self.user.check_password(self.invalid_new_password))

    def test_password_recovery_confirm(self):
        response = self.client.post(self.url, {'token': self.token, 'new_password': self.new_password})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that token was deleted from db
        self.assertFalse(PasswordRecoveryToken.objects.filter(pk=self.recovery_token.pk).exists())

        self.user.refresh_from_db()  # refresh user to be able to check password update

        # check that password has changed
        self.assertTrue(self.user.check_password(self.new_password))
