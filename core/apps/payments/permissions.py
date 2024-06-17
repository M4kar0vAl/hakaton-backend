from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return type(request.user) is User
