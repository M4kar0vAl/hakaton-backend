from django.db import models

from datetime import timedelta

from core.apps.accounts.models import User


# Тариф
class Tariff(models.Model):
    name = models.CharField(max_length=100, verbose_name='Тариф')
    cost = models.PositiveIntegerField(verbose_name='Цена')
    duration = models.DurationField(verbose_name='Продолжительность')

    class Meta:
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'

    def __repr__(self):
        return f'Тариф: {self.name}'


# Подписка
class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True)

    def __str__(self):
        return f'{self.user.email} - {self.tariff.name}'
    
    def activate(self):
        self.is_active = True
        self.end_date = self.start_date + timedelta
        self.save()
    

# Промокод
class PromoCode(models.Model):
    code = models.CharField('Промокод', max_length=30)
    discount = models.IntegerField()
