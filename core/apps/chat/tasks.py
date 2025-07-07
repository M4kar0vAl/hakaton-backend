from celery import shared_task
from django.conf import settings
from django.utils import timezone

from core.apps.chat.models import MessageAttachment, Room


@shared_task
def message_attachments_cleanup():
    life_time_ago = timezone.now() - settings.MESSAGE_ATTACHMENT_DANGLING_LIFE_TIME
    MessageAttachment.objects.filter(message__isnull=True, created_at__lte=life_time_ago).delete()


@shared_task
def empty_rooms_cleanup():
    Room.objects.filter(participants__isnull=True).delete()
