from django.db import models

from core.apps.brand.models import Brand


class MatchActivity(models.Model):
    initiator = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, related_name='activity_as_initiator', null=True, verbose_name='Кто лайкнул'
    )
    target = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, related_name='activity_as_target', null=True, verbose_name='Кого лайкнули'
    )
    is_match = models.BooleanField(verbose_name='Метч')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

