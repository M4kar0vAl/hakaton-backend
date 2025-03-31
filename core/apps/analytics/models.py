from django.db import models

from core.apps.brand.models import Brand


class BrandActivity(models.Model):
    REGISTRATION = 'R'
    DELETION = 'D'
    PAYMENT = 'P'
    ACTION_CHOICES = {
        REGISTRATION: 'Registration',
        DELETION: 'Deletion',
        PAYMENT: 'Payment'
    }
    brand = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name='activity', verbose_name='Бренд'
    )
    action = models.CharField(max_length=1, choices=ACTION_CHOICES, verbose_name='Действие')
    performed_at = models.DateTimeField(auto_now_add=True, verbose_name='Выполнено')
