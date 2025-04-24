from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.models import PasswordRecoveryToken

User = get_user_model()


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPOGATES=True
)
class PasswordRecoveryCreateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.email = 'user1@example.com'
        cls.non_existent_email = 'non-existent@example.com'

        cls.user = User.objects.create_user(
            email=cls.email,
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.url = reverse('password_recovery-list')

    def test_password_recovery_create_user_does_not_exist(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, {'email': self.non_existent_email})

        # must return 200 to prevent information leakage
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that token was not created in db
        self.assertFalse(PasswordRecoveryToken.objects.filter(user__email=self.non_existent_email).exists())

        # check that email was not sent
        self.assertEqual(len(mail.outbox), 0)

    def test_password_recovery_create(self):
        # used to emulate sending email via celery task which is called using .delay_on_commit()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, {'email': self.email})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data)

        # check that token was created in db
        self.assertTrue(PasswordRecoveryToken.objects.filter(user=self.user).exists())

        # check that email was sent
        self.assertEqual(len(mail.outbox), 1)

        email_message = mail.outbox[0]

        # check that email was sent to only one person and to the correct email address
        self.assertEqual(len(email_message.to), 1)
        self.assertEqual(email_message.to[0], self.email)

    def test_password_recovery_create_token_for_user_already_exists(self):
        recovery_token = PasswordRecoveryToken.objects.create(
            user=self.user,
            token='token'
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, {'email': self.email})

        # must return 200 to prevent information leakage
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that another token was not created in db
        self.assertEqual(PasswordRecoveryToken.objects.filter(user=self.user).count(), 1)

        # check that token hasn't changed
        self.assertTrue(PasswordRecoveryToken.objects.filter(
            user=recovery_token.user,
            token=recovery_token.token,
            created=recovery_token.created
        ).exists())

        # check that email was not sent
        self.assertEqual(len(mail.outbox), 0)

    def test_password_recovery_create_returns_200_no_matter_what(self):
        # created
        response = self.client.post(self.url, {'email': self.email})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # already exists for the user with this email
        response1 = self.client.post(self.url, {'email': self.email})

        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # user with the given email does not exist
        response2 = self.client.post(self.url, {'email': self.non_existent_email})

        self.assertEqual(response2.status_code, status.HTTP_200_OK)
