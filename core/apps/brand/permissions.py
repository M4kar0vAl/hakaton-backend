from rest_framework import permissions


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
        return request.user.brand.subscription.name == 'Бизнес'  # TODO change definition of business sub
