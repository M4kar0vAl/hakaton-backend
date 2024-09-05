from django.conf import settings
from django.db import models


class Room(models.Model):
    MATCH = 'M'
    INSTANT = 'I'
    SUPPORT = 'S'
    HELP = 'H'
    TYPE_CHOICES = {
        MATCH: 'Match',
        INSTANT: 'Instant',
        SUPPORT: 'Support',
        HELP: 'Help'
    }
    participants = models.ManyToManyField(to=settings.AUTH_USER_MODEL, related_name='rooms', verbose_name='Участники')
    has_business = models.BooleanField(default=False, verbose_name='Бизнес тариф')
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default=MATCH, verbose_name='Тип')

    def __repr__(self):
        return f'Room {self.pk}: {self.type}'


class Message(models.Model):
    text = models.TextField(verbose_name='Текст сообщения')
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='messages',
                             verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    room = models.ForeignKey(to=Room, on_delete=models.CASCADE, related_name='messages', verbose_name='Чат')

    def __repr__(self):
        return f'Message by user: {self.user} in room: {self.room.pk}'
