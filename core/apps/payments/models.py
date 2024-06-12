from django.db import models


class Subscription(models.Model):
    name = models.CharField(max_length=100, verbose_name='Тариф')
    cost = models.PositiveIntegerField(verbose_name='Цена')
    duration = models.DurationField(verbose_name='Продолжительность')

    class Meta:
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'

    def __repr__(self):
        return f'Тариф: {self.name}'


class PromoCode(models.Model):
    code = models.CharField('Промокод', max_length=30)
