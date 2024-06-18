from rest_framework.permissions import BasePermission


class IsBot(BasePermission):
    def has_permission(self, request, view):
        return True
