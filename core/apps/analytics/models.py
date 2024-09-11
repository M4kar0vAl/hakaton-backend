from django.db import models

from core.apps.brand.models import Brand, Collaboration


class MatchActivity(models.Model):
    initiator = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name='activity_as_initiator', verbose_name='Кто лайкнул'
    )
    target = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name='activity_as_target', verbose_name='Кого лайкнули'
    )
    is_match = models.BooleanField(verbose_name='Метч')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    collab = models.ForeignKey(
        Collaboration, on_delete=models.PROTECT, related_name='activity', null=True, verbose_name='Коллаборация'
    )


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
