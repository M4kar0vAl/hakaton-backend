from typing import Dict, Any

from channels.consumer import AsyncConsumer
from django.contrib.auth import get_user_model
from djangochannelsrestframework.permissions import IsAuthenticated, BasePermission

User = get_user_model()


class IsAuthenticatedConnect(IsAuthenticated):
    async def can_connect(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, message=None
    ) -> bool:
        user = scope.get('user')
        if type(user) is User:
            return user.is_authenticated
        return False


class IsAdminUser(BasePermission):
    async def has_permission(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, action: str, **kwargs
    ) -> bool:
        user = scope.get('user')
        if not type(user) is User:
            return False

        return user.is_staff

    async def can_connect(
            self, scope: Dict[str, Any], consumer: AsyncConsumer, message=None
    ) -> bool:
        user = scope.get('user')
        if not type(user) is User:
            return False

        return user.is_staff
