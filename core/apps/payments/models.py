import uuid

from dateutil.relativedelta import relativedelta
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

    def get_duration_as_relativedelta(self):
        total_days = self.duration.days
        months = total_days // 30
        days = total_days % 30

        return relativedelta(months=months, days=days)


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
        to='Tariff',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sub_upgraded_to',
        verbose_name='Апгрейд c'
    )
    upgraded_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата-время апгрейда')
    gift_promocode = models.OneToOneField(
        to='GiftPromoCode',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subscription',
        verbose_name='Подарочный промокод'
    )  # if null => bought by himself, if not null => was gifted by someone

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'Subscription: [{self.tariff} expires at {self.end_date.date()}]'

    def __repr__(self):
        return (
            f'{self.__class__.__name__}(brand_id={self.brand_id}, tariff_id={self.tariff_id}, '
            f'end_date="{self.end_date}", is_active={self.is_active}, promocode_id={self.promocode_id}, '
            f'upgraded_from_id={self.upgraded_from_id}, upgraded_at={self.upgraded_at}, '
            f'gift_promocode_id={self.gift_promocode_id})'
        )


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

    def is_used_by_brand(self, brand):
        # check if promo code was used when purchasing subscription
        if brand.subscriptions.filter(promocode=self).exists():
            return True

        # check if promo code was used when purchasing a gift
        if brand.gifts_as_giver.filter(promocode=self).exists():
            return True

        return False


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

    class Meta:
        verbose_name = 'Gift PromoCode'
        verbose_name_plural = 'Gift PromoCodes'

    def __str__(self):
        return f'Gift PromoCode: [{self.code} - {self.tariff}]'

    def __repr__(self):
        # cannot recreate, because "code" must be unique
        return (
            f'{self.__class__.__name__}(code="{self.code}", tariff_id={self.tariff_id}, expires_at="{self.expires_at}", '
            f'giver_id={self.giver_id}, is_used={self.is_used}, promocode_id={self.promocode_id})'
        )
