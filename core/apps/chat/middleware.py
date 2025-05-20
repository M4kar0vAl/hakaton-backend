import os

import django
import jwt
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.utils import datetime_from_epoch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.config.settings')
django.setup()

from django.contrib.auth.models import AnonymousUser  # MUST be called after configuring settings

ALGORITHM = "HS256"

User = get_user_model()


@database_sync_to_async
def get_user(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=ALGORITHM)
    except Exception:
        return AnonymousUser()

    token_exp = datetime_from_epoch(payload['exp'])
    if token_exp <= timezone.now():
        return AnonymousUser()

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return AnonymousUser()

    return user


class TokenAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):
        try:
            protocols = scope['subprotocols']

            if protocols:
                # if protocols specified
                token_key = protocols.pop()  # last protocol MUST be a token
                scope['subprotocols'] = protocols  # override with valid protocols

                headers = dict(scope['headers'])  # copy headers
                header_protocols = headers[b'sec-websocket-protocol'].split(b', ')  # get protocols from headers
                header_protocols.pop()  # remove last protocol (token)

                if header_protocols:
                    # if there are protocols after removing token, then override header protocols
                    headers[b'sec-websocket-protocol'] = b', '.join(header_protocols)
                else:
                    # if token was the only protocol, then remove protocols header
                    headers.pop(b'sec-websocket-protocol')

                scope['headers'] = list(headers.items())  # override with valid headers
            else:
                # if client didn't send protocols
                token_key = None
        except KeyError:
            token_key = None

        scope['user'] = await get_user(token_key)

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return TokenAuthMiddleware(inner)
