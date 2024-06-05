from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema

from core.apps.accounts import serializers


class Fix1(OpenApiViewExtension):
    """
    Дополнение описания эндпоинтов авторизации.
    """
    target_class = 'core.apps.accounts.api.UserViewSet'

    def view_replacement(self):
        class Fixed(self.target_class):
            @extend_schema(description='Создать пользователя',
                           responses=serializers.CreateUserSerializer,
                           )
            def create(self, request, *args, **kwargs):
                return super().create(request, *args, **kwargs)

            @extend_schema(description='Смена пароля пользователя',
                           responses=serializers.UserSerializer,
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
        class Fixed(self.target_class):
            """Получение новой пары токенов по refresh токену"""
            pass

        return Fixed


def user_me_postprocessing_hook(result, generator, request, public):
    """
    Корректировка описания эндпоинта auth/users/me,
    описания разделены по методам
    """
    description = {
        'get': {'description': 'Получить данные авторизованного пользователя'},
        'patch': {'description': 'Выборочно обновить данные авторизованного пользователя'},
        'delete': {'description': 'Удалить авторизованного пользователя'},
    }

    methods = ['get', 'patch', 'delete']
    endpoints = ['/auth/users/me/']

    for endpoint in endpoints:
        for method in methods:
            schema = result['paths'][endpoint][method]
            schema.update(description[method])

    return result
