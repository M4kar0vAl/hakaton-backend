from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.apps.accounts.factories import PasswordRecoveryTokenFactory
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
        cls.recovery_token = PasswordRecoveryTokenFactory()
        cls.expired_recovery_token = PasswordRecoveryTokenFactory(expired=True)

        cls.task = password_recovery_tokens_cleanup

    def test_password_recovery_tokens_cleanup_task(self):
        self.task.delay()

        self.assertTrue(
            PasswordRecoveryToken.objects.filter(pk=self.recovery_token.pk).exists()
        )

        self.assertFalse(
            PasswordRecoveryToken.objects.filter(pk=self.expired_recovery_token.pk).exists()
        )
