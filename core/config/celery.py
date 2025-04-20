import os
from datetime import timedelta

from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.config.settings')

app = Celery('core.config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'message_attachments_cleanup': {
        'task': 'core.apps.chat.tasks.message_attachments_cleanup',
        'schedule': settings.MESSAGE_ATTACHMENT_DANGLING_LIFE_TIME
    },
    'deactivate_expired_subscriptions': {
        'task': 'core.apps.payments.tasks.deactivate_expired_subscriptions',
        'schedule': timedelta(hours=1)
    }
}
