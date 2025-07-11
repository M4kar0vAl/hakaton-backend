import os

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.common.utils import get_random_filename_with_extension


def room_directory_path(instance, filename):
    new_filename = get_random_filename_with_extension(filename)

    return os.path.join('message_attachments', new_filename)


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

    class Meta:
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'

    def __str__(self):
        return f'Room {self.pk}: {self.get_type_display()}'

    def __repr__(self):
        return f'{self.__class__.__name__}(type="{self.type}")'


class Message(models.Model):
    text = models.TextField(verbose_name='Текст сообщения')
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='messages',
                             verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    room = models.ForeignKey(to=Room, on_delete=models.CASCADE, related_name='messages', verbose_name='Чат')

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        display_text = self.text

        if len(self.text) > 20:
            display_text = f'{display_text[:20]}...'

        return f'Message {display_text}'

    def __repr__(self):
        return f'{self.__class__.__name__}(text="{self.text}", user_id={self.user_id}, room_id={self.user_id})'


class MessageAttachment(models.Model):
    message = models.ForeignKey(
        to=Message,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=None,
        related_name='attachments',
        verbose_name='Сообщение'
    )

    file = models.FileField(upload_to=room_directory_path, verbose_name='Прикрепленный файл')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        verbose_name = 'Message Attachment'
        verbose_name_plural = 'Message Attachments'

    def __str__(self):
        return f'Attachment {self.pk} for message {self.message_id}'

    def __repr__(self):
        return f'{self.__class__.__name__} {self.pk}'

    @property
    def is_expired(self):
        return self.created_at + settings.MESSAGE_ATTACHMENT_DANGLING_LIFE_TIME <= timezone.now()


class RoomFavorites(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='room_favorites', verbose_name='Пользователь'
    )

    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='as_favorite', verbose_name='Комната'
    )

    class Meta:
        verbose_name = 'Room Favorites'
        verbose_name_plural = 'Room Favorites'

    def __str__(self):
        return f'Favorite room {self.room_id} for user {self.user_id}'

    def __repr__(self):
        return f'{self.__class__.__name__}(user_id={self.user_id}, room_id={self.room_id})'
