from django.conf import settings
from django.db import models


class Room(models.Model):
    MATCH = 'M'
    INSTANT = 'I'
    SUPPORT = 'S'
    TYPE_CHOICES = {
        MATCH: 'Match',
        INSTANT: 'Instant',
        SUPPORT: 'Support',
    }
    participants = models.ManyToManyField(to=settings.AUTH_USER_MODEL, related_name='rooms', verbose_name='Участники')
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default=MATCH, verbose_name='Тип')

    def __str__(self):
        return f'Room {self.pk}: {self.type}'


class Message(models.Model):
    text = models.TextField(verbose_name='Текст сообщения')
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='messages',
                             verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    room = models.ForeignKey(to=Room, on_delete=models.CASCADE, related_name='messages', verbose_name='Чат')

    def __str__(self):
        return f'Message in room {self.room_id}: {self.text[:20]}'


class RoomFavorites(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='room_favorites', verbose_name='Пользователь'
    )

    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='as_favorite', verbose_name='Комната'
    )

    def __str__(self):
        return f'Favorite room {self.room_id} for user {self.user_id}'

    def __repr__(self):
        return f'{self.__class__.__name__}(user_id={self.user_id}, room_id={self.room_id})'
