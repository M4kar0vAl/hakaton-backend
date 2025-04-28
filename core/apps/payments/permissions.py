from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import permissions

User = get_user_model()


class CanUpgradeTariff(permissions.BasePermission):
    def has_permission(self, request, view):
        current_sub = request.user.brand.get_active_subscription(True)

        if current_sub is None:
            return False

        # can upgrade only from Lite tariff
        # Trial doesn't have cost, so should use subscribe endpoint to upgrade Trial
        return current_sub.tariff.name == 'Lite Match'


class HasActiveSub(permissions.BasePermission):
    """
    Allow access only to brands that have an active subscription.
    """
    def has_permission(self, request, view):
        return request.user.brand.get_active_subscription() is not None


class IsBusinessSub(permissions.BasePermission):
    """
    Allow access only to brands with business subscription.
    """
    def has_permission(self, request, view):
        return request.user.brand.subscriptions.filter(
            is_active=True, end_date__gt=timezone.now(), tariff__name='Business Match'
        ).exists()
