from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions

from core.apps.brand.models import Match


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Проверка прав на уровне объекта.
    Только пользователь, связанный с брендом или администратор могут редактировать и удалять карточку бренда.
    Остальным доступны только безопасные методы ('GET', 'HEAD', 'OPTIONS')
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS or request.user.is_staff:
            return True

        return obj.user == request.user


class IsBrand(permissions.BasePermission):
    """
    Allow access only to users that have brand associated with them.
    Users, that may not have brand:
      - admins
      - users on trial subscription
    """
    def has_permission(self, request, view):
        return hasattr(request.user, 'brand')


class IsBusinessSub(permissions.BasePermission):
    """
    Allow access only to brands with business subscription.
    """
    def has_permission(self, request, view):
        return request.user.brand.subscriptions.filter(
            is_active=True, end_date__gt=timezone.now(), tariff__name='Business Match'
        ).exists()


class CanInstantCoop(permissions.BasePermission):
    """
    Allow access to brands that liked the target and don't have match with it
    """
    def has_permission(self, request, view):
        current_brand_id = request.user.brand.id
        target_id = request.data['target']

        # no need to check for match because
        # access allowed only if the current brand liked the target but don't have match with it yet.
        # It means that access allowed only if the current brand
        # is the initiator and haven't received like in response yet
        has_liked_target = Match.objects.filter(
            initiator_id=current_brand_id,
            target_id=target_id,
            is_match=False
        ).exists()

        return has_liked_target
