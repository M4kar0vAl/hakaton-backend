import jwt
from rest_framework.permissions import BasePermission
from jwt.exceptions import InvalidSignatureError, DecodeError
from django.conf import settings


class IsBot(BasePermission):
    def has_permission(self, request, view):
        try:
            token = request.META.get('HTTP_X_INTERNAL_REQUEST')
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                'HS256'
            )
        except (InvalidSignatureError, DecodeError):
            return False

        if payload.get('bot') == settings.BOT_URL:
            return True

        return False
