from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema

from core.apps.accounts import serializers


class Fix1(OpenApiViewExtension):
    """
    Описание эндпоинтов
    """
    target_class = 'core.apps.payments.api.PaymentViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Payment'])
        class Fixed(self.target_class):
            @extend_schema(description='Список всех тарифов')
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

        return Fixed
