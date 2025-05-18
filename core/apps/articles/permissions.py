from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from rest_framework import permissions

User = get_user_model()


class IsStaff(permissions.BasePermission):
    """
    Allows access to staff users and superusers only when using session authentication (from admin panel).
    """

    def has_permission(self, request, view):
        session_key = request.session.session_key

        if session_key is None:
            return False

        s = Session.objects.get(pk=session_key)
        user_id = s.get_decoded().get('_auth_user_id')

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            user = None

        return user is not None and (user.is_staff or user.is_superuser)
