import uuid

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
        return f'{self.__class__.__name__}(name="{self.name}", cost={self.cost}, duration="{self.duration}")'


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
    upgraded_from = models.ForeignKey(
        to='Tariff', on_delete=models.PROTECT, null=True, related_name='sub_upgraded_to', verbose_name='Апгрейд c'
    )
    upgraded_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата-время апгрейда')
    gift_promocode = models.OneToOneField(
        to='GiftPromoCode',
        on_delete=models.PROTECT,
        null=True,
        related_name='subscription',
        verbose_name='Подарочный промокод'
    )  # if null => bought by himself, if not null => was gifted by someone

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
        return f'PromoCode: {self.code} | {self.discount}%'

    def __repr__(self):
        # cannot recreate, because "code" must be unique
        return f'{self.__class__.__name__}(code="{self.code}", discount={self.discount}, expires_at="{self.expires_at}")'


class GiftPromoCode(models.Model):
    code = models.UUIDField(unique=True, default=uuid.uuid4, verbose_name='Код')
    tariff = models.ForeignKey(to=Tariff, on_delete=models.PROTECT, verbose_name='Тариф')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    expires_at = models.DateTimeField(verbose_name='Истекает')
    giver = models.ForeignKey(
        to=Brand, on_delete=models.PROTECT, related_name='gifts_as_giver', verbose_name='Даритель'
    )
    is_used = models.BooleanField(default=False, verbose_name='Использован')
    promocode = models.ForeignKey(
        to='PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gift_promocodes',
        verbose_name='Промокод'
    )  # use common promo code to get discount
