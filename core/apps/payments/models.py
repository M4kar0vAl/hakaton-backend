from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from core.apps.brand.models import Brand


class Tariff(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    cost = models.PositiveIntegerField(verbose_name='Цена')
    duration = models.DurationField(verbose_name='Продолжительность')

    class Meta:
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'

    def __str__(self):
        return f'Тариф: {self.name} - {self.duration.days} days'

    def __repr__(self):
        return f'Тариф: {self.name} - {self.duration.days} days'


class Subscription(models.Model):
    brand = models.ForeignKey(to=Brand, on_delete=models.PROTECT, related_name='subscriptions', verbose_name='Бренд')
    tariff = models.ForeignKey(to=Tariff, on_delete=models.PROTECT, related_name='subscriptions', verbose_name='Тариф')
    start_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата начала подписки')
    end_date = models.DateTimeField(verbose_name='Дата окончания подписки')
    is_active = models.BooleanField(default=False, verbose_name='Активна')
    promocode = models.ForeignKey(
        to='PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscriptions',
        verbose_name='Промокод'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'Подписка: {self.start_date.date()} - {self.end_date.date()}'

    def __repr__(self):
        return f'Подписка: {self.start_date.date()} - {self.end_date.date()}'


class PromoCode(models.Model):
    code = models.CharField(max_length=30, unique=True, verbose_name='Промокод')
    discount = models.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        verbose_name='Скидка, %')
    expires_at = models.DateTimeField(verbose_name='Истекает')

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'

    def __str__(self):
        return f'Промокод: {self.code} - {self.discount}'

    def __repr__(self):
        return f'Промокод: {self.code} - {self.discount}'
