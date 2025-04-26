from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F
from django.test import TestCase, override_settings

from core.apps.accounts.models import PasswordRecoveryToken
from core.apps.accounts.tasks import password_recovery_tokens_cleanup

User = get_user_model()


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPOGATES=True
)
class PasswordRecoveryTokensCleanupTaskTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2 = User.objects.bulk_create([
            User(
                email=f'user{i}@example.com',
                phone='+79993332211',
                fullname='Юзеров Юзер Юзерович',
                password='Pass!234',
                is_active=True
            )
            for i in range(2)
        ])

        cls.recovery_token, cls.expired_recovery_token = PasswordRecoveryToken.objects.bulk_create([
            PasswordRecoveryToken(
                user=user,
                token='token'
            )
            for user in [cls.user1, cls.user2]
        ])

        cls.expired_recovery_token.created = F('created') - timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
        cls.expired_recovery_token.save()

        cls.task = password_recovery_tokens_cleanup

    def test_password_recovery_tokens_cleanup_task(self):
        self.task.delay()

        self.assertTrue(
            PasswordRecoveryToken.objects.filter(pk=self.recovery_token.pk).exists()
        )

        self.assertFalse(
            PasswordRecoveryToken.objects.filter(pk=self.expired_recovery_token.pk).exists()
        )
