from django.contrib.auth import get_user_model

User = get_user_model()


class AuthBackend(object):
    """
    Кастомный бекэнд для возможности расширения способов аутентификации пользователей
    """
    supports_object_permissions = True
    supports_anonymous_user = False
    supports_inactive_user = False

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def authenticate(self, request, email, password):
        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:
            return None

        if user.check_password(password):
            return user

        else:
            return None
