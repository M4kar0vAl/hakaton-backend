from rest_framework import permissions

from core.apps.blacklist.models import BlackList
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


class IsNotCurrentBrand(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.brand.id != obj.id


class IsBrand(permissions.BasePermission):
    """
    Allow access only to users that have brand associated with them.
    Users, that may not have brand:
      - admins
      - users on trial subscription
    """

    def has_permission(self, request, view):
        return hasattr(request.user, 'brand')


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


class NotInBlacklistOfTarget(permissions.BasePermission):
    """
    Allow access only to brands that are not in target brand's blacklist.
    """

    def has_permission(self, request, view):
        action = view.action

        target_id = request.data.get('target')

        if action == 'retrieve':
            target_id = view.kwargs.get('pk')

        if target_id is None:
            return False

        current_brand = request.user.brand

        return not BlackList.objects.filter(initiator_id=target_id, blocked=current_brand).exists()


class DidNotBlockTarget(permissions.BasePermission):
    """
    Allow access only to brands that have not blocked the target.
    """

    def has_permission(self, request, view):
        target_id = request.data.get('target')

        if target_id is None:
            return False

        current_brand = request.user.brand

        return not BlackList.objects.filter(initiator=current_brand, blocked_id=target_id).exists()
