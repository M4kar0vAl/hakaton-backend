from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema

from core.apps.analytics.serializers import LogPaymentSerializer


class Fix1(OpenApiViewExtension):
    target_class = 'core.apps.analytics.api.BrandActivityViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Brand Activity'])
        class Fixed(self.target_class):
            @extend_schema(
                tags=['Brand Activity'],
                description='Log payment action performed by the brand.\n\n'
                            'Authenticated brand only.',
                responses={201: LogPaymentSerializer},
            )
            def log_payment(self, request, *args, **kwargs):
                return super().log_payment(request, *args, **kwargs)

        return Fixed
