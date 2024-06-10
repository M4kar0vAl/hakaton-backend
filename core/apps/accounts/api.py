import os

from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.response import Response

from core.apps.accounts.serializers import UserSerializer
from telegram_bot.conf import (
    REDIS_USER,
    REDIS_PASS,
    REDIS_HOST,
    REDIS_PORT,
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer


import redis
import json
from rest_framework.decorators import api_view


@api_view(['POST'])
def test(request):
    my_relegram_id = os.getenv("TELEGRAM_ID")
    redis_client = redis.Redis(
        username=f'{REDIS_USER}',
        password=f'{REDIS_PASS}',
        host=f'{REDIS_HOST}',
        port=f'{REDIS_PORT}',
        db=0
    )
    data = {
        'message': "message",
        'users': [my_relegram_id, ],
    }
    redis_client.publish('organizer', json.dumps(data))
    return Response(status=200)
