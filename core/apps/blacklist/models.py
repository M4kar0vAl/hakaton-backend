from django.db import models

from core.apps.brand.models import Brand


class BlackList(models.Model):
    initiator = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name='blacklist_as_initiator', verbose_name='Добавил в ЧС'
    )

    blocked = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name='blacklist_as_blocked', verbose_name='Заблокирован'
    )

    def __str__(self):
        return f'BlacklistItem: initiator - {self.initiator_id} | blocked - {self.blocked_id}'

    def __repr__(self):
        return f'{self.__class__.__name__}(initiator={self.initiator}, blocked={self.blocked})'
