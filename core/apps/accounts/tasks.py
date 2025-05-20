from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from core.apps.accounts.models import PasswordRecoveryToken


@shared_task
def send_password_recovery_email(email: str, token: str):
    text = (
        f'Ваш токен для восстановления пароля: {token}.\n\n'
        f'Используйте его в приложении, чтобы задать новый пароль для своего аккаунта.'
    )

    send_mail(
        'Восстановление пароля в приложении W2W',
        text,
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False
    )


@shared_task
def password_recovery_tokens_cleanup():
    life_time_ago = timezone.now() - timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
    PasswordRecoveryToken.objects.filter(created__lte=life_time_ago).delete()
