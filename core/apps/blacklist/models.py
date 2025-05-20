from django.db import models

from core.apps.brand.models import Brand


class BlackList(models.Model):
    initiator = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name='blacklist_as_initiator', verbose_name='Добавил в ЧС'
    )

    blocked = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name='blacklist_as_blocked', verbose_name='Заблокирован'
    )

    class Meta:
        verbose_name = 'Blacklist'
        verbose_name_plural = 'Blacklist'

    def __str__(self):
        return f'Blacklist [{self.initiator} blocked {self.blocked}]'

    def __repr__(self):
        return f'{self.__class__.__name__}(initiator_id={self.initiator_id}, blocked_id={self.blocked_id})'
