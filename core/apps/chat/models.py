from django.conf import settings
from django.db import models

from core.apps.brand.models import Brand


class Room(models.Model):
    participants = models.ManyToManyField(to=Brand, related_name='rooms', verbose_name='Участники')
    has_business = models.BooleanField(default=False, verbose_name='Бизнес тариф')

    def __repr__(self):
        return f'Room {self.pk}'


class Message(models.Model):
    text = models.TextField(verbose_name='Текст сообщения')
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='messages',
                             verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    room = models.ForeignKey(to=Room, on_delete=models.CASCADE, related_name='messages', verbose_name='Чат')

    def __repr__(self):
        return f'Message by user: {self.user} in room: {self.room.pk}'
