from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import (
    UserFactory,
    PasswordRecoveryTokenFactory,
    PasswordRecoveryTokenExpiredFactory
)
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

        cls.user = UserFactory()
        cls.recovery_token = PasswordRecoveryTokenFactory(user=cls.user, token=get_recovery_token_hash(cls.token))

        cls.url = reverse('password_recovery-confirm')

    def test_password_recovery_confirm_token_does_not_exist(self):
        response = self.client.post(self.url, {'token': self.non_existent_token, 'new_password': self.new_password})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()  # refresh user to be able to check password update

        # check that password haven't changed
        self.assertFalse(self.user.check_password(self.new_password))

    def test_password_recovery_confirm_token_expired(self):
        expired_token = 'svdjkml'
        expired_recovery_token = PasswordRecoveryTokenExpiredFactory(token=get_recovery_token_hash(expired_token))

        response = self.client.post(self.url, {'token': expired_token, 'new_password': self.new_password})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check that token remains in db
        self.assertTrue(PasswordRecoveryToken.objects.filter(pk=expired_recovery_token.pk).exists())

        expired_recovery_token.user.refresh_from_db()  # refresh user to be able to check password update

        # check that password haven't changed
        self.assertFalse(expired_recovery_token.user.check_password(self.new_password))

    def test_password_recovery_confirm_new_password_is_too_simple(self):
        response = self.client.post(self.url, {'token': self.token, 'new_password': self.invalid_new_password})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check that token remains in db
        self.assertTrue(PasswordRecoveryToken.objects.filter(pk=self.recovery_token.pk).exists())

        self.user.refresh_from_db()  # refresh user to be able to check password update

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
