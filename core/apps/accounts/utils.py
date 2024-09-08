from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings


def send_password_recovery_email(email, token, host):
    send_mail(
        'Восстановление пароля',
        'Восстановите ваш пароль. Перейдите по ссылке: ' + host + reverse('recovery_password', kwargs={'token': token}),
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False
    )