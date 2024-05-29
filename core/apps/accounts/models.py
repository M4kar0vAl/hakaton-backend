from django.db import models
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser

from .manager import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField('Эл. почта', unique=True)
    phone = models.CharField("Телефон", max_length=12)
    date_joined = models.DateTimeField('Дата создания', auto_now_add=True)
    is_active = models.BooleanField('Активирован', default=True)  # обязательно
    is_staff = models.BooleanField('Организатор', default=False)  # для админ панели

    sub_expire = models.DateField("Окончание подписки", null=True)

    objects = UserManager()  # используется кастомный менеджер юзера

    USERNAME_FIELD = 'email'  # поле, используемое в качестве логина
    REQUIRED_FIELDS = ['phone']  # дополнительные поля при регистрации

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __repr__(self):
        return f"User {self.email}"


class Subscription(models.Model):
    name = models.CharField(max_length=100, verbose_name='Тариф')
    cost = models.PositiveIntegerField(verbose_name='Цена')

    class Meta:
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'

    def __repr__(self):
        return f'Тариф: {self.name}'
