from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from core.apps.accounts.serializers import CreateUserSerializer, UserSerializer


class Fix1(OpenApiViewExtension):
    """
    Дополнение описания эндпоинтов авторизации.
    """
    target_class = 'core.apps.accounts.api.UserViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Authentication'])
        class Fixed(self.target_class):
            @extend_schema(
                tags=['Authentication'],
                description='Создать пользователя',
                responses=CreateUserSerializer,
            )
            def create(self, request, *args, **kwargs):
                return super().create(request, *args, **kwargs)

            @extend_schema(
                tags=['Authentication'],
                description='Смена пароля пользователя',
                responses=UserSerializer,
            )
            def password_reset(self, request, *args, **kwargs):
                return super().password_reset(request, *args, **kwargs)

        return Fixed


class Fix2(OpenApiViewExtension):
    """
    Описаие к эндпоинту получения JWT токенов.
    """
    target_class = 'rest_framework_simplejwt.views.TokenObtainPairView'

    def view_replacement(self):
        @extend_schema(tags=['Authentication'])
        class Fixed(self.target_class):
            """
            Создает пару JWT токенов: access_token и refresh_token.\n\n
            Для авторизации access_token всегда передается с префиксом "Bearer" через пробел, например:\n\n
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjk1MTM5MTYzLCJpYXQiO"
            """
            pass

        return Fixed


class Fix3(OpenApiViewExtension):
    """
    Описаие к эндпоинту обновления JWT access токена.
    """
    target_class = 'rest_framework_simplejwt.views.TokenRefreshView'

    def view_replacement(self):
        @extend_schema(tags=['Authentication'])
        class Fixed(self.target_class):
            """Получение новой пары токенов по refresh токену"""
            pass

        return Fixed


class Fix4(OpenApiViewExtension):
    target_class = 'core.apps.accounts.api.PasswordRecoveryViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Authentication'])
        class Fixed(self.target_class):
            @extend_schema(
                tags=['Authentication'],
                description="Request password recovery.\n\n"
                            "\temail: user's email where token will be sent\n\n"
                            "Code 200 will be regardless of whether the user with the given email exists.",
                responses={200: None}
            )
            def create(self, request, *args, **kwargs):
                return super().create(request, *args, **kwargs)

            @extend_schema(
                tags=['Authentication'],
                description="Confirm password recovery.\n\n"
                            "\ttoken: token that was sent to the user by email\n\n"
                            "\tnew_password: password to set as the user new password\n\n",
                responses={
                    200: inline_serializer(
                        name='password_recovery_confirm_200',
                        fields={'response': serializers.CharField(default='Password successfully reset!')}
                    ),
                    400: inline_serializer(
                        name='password_recovery_confirm_400',
                        fields={
                            'token': serializers.ListField(child=serializers.CharField()),
                            'new_password': serializers.ListField(child=serializers.CharField())
                        }
                    ),
                }
            )
            def confirm(self, request, *args, **kwargs):
                return super().confirm(request, *args, **kwargs)

        return Fixed


def user_me_postprocessing_hook(result, generator, request, public):
    """
    Корректировка описания эндпоинта auth/users/me,
    описания разделены по методам
    """
    description = {
        'get': {'description': 'Получить данные авторизованного пользователя'},
        'patch': {'description': 'Выборочно обновить данные авторизованного пользователя'},
    }

    methods = ['get', 'patch']
    endpoints = ['/auth/users/me/']

    for endpoint in endpoints:
        for method in methods:
            schema = result['paths'][endpoint][method]
            schema.update(description[method])

    return result
