from celery import shared_task
from django.utils import timezone

from core.apps.payments.models import Subscription


@shared_task
def deactivate_expired_subscriptions():
    Subscription.objects.filter(is_active=True, end_date__lte=timezone.now()).update(is_active=False)
