import hashlib

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.crypto import get_random_string


def send_password_recovery_email(email, token, host):
    send_mail(
        'Восстановление пароля',
        'Восстановите ваш пароль. Перейдите по ссылке: ' + host + reverse('recovery_password', kwargs={'token': token}),
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False
    )


def get_recovery_token():
    return get_random_string(22)


def get_recovery_token_hash(token: str):
    return hashlib.sha256(token.encode()).hexdigest()
