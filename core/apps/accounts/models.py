from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from .manager import UserManager
from .validators import phone_validator


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField('Эл. почта', unique=True)
    phone = models.CharField(
        "Телефон",
        max_length=12,
        validators=[phone_validator, ]
    )
    fullname = models.CharField(max_length=512, verbose_name='ФИО')
    date_joined = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )
    is_active = models.BooleanField(
        'Активирован', default=True
    )  # обязательно
    is_staff = models.BooleanField(
        'Организатор', default=False
    )  # для админ панели

    objects = UserManager()  # используется кастомный менеджер юзера

    USERNAME_FIELD = 'email'  # поле, используемое в качестве логина
    REQUIRED_FIELDS = ['phone']  # дополнительные поля при регистрации

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"User {self.email}"

    def __repr__(self):
        return (
            f'{self.__class__.__name__}(email="{self.email}", phone="{self.phone}", fullname="{self.fullname}", '
            f'is_active={self.is_active}, is_staff={self.is_staff})'
        )


class PasswordRecovery(models.Model):
    # TODO сделать автоматическую очистку устаревших моделей
    email = models.EmailField()
    token = models.CharField()
    created = models.DateTimeField(auto_now_add=True)
