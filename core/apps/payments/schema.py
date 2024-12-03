from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema

from core.apps.payments.serializers import SubscriptionSerializer


class Fix1(OpenApiViewExtension):
    """
    Описание эндпоинтов
    """
    target_class = 'core.apps.payments.api.TariffViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Tariffs'])
        class Fixed(self.target_class):
            @extend_schema(
                description="Get a list of tariffs.\n\n"
                            "duration field is a string in format: 'DD HH:MM:ss'\n\n"
                            "\tD - number of days\n\n"
                            "\tH - number of hours\n\n"
                            "\tM - number of minutes\n\n"
                            "\ts - number of seconds\n\n"
                            "When displaying duration to the user, 30 days = 1 month should be assumed.\n\n"
                            "Authenticated only."
            )
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

            @extend_schema(
                tags=['Tariffs'],
                description="Subscribe to the tariff.\n\n"
                            "\ttariff: tariff id\n\n"
                            "\tpromocode: promocode id\n\n"
                            "To get the promocode id, you must first check the promocode entered by the user "
                            "by making request to /api/v1/promocodes/{code}/.\n\n"
                            "In response you will get info about promocode including its id.\n\n"
                            "Authenticated brand only.",
                responses={201: SubscriptionSerializer}
            )
            def subscribe(self, request, *args, **kwargs):
                return super().subscribe(request, *args, **kwargs)

            @extend_schema(
                tags=['Tariffs'],
                description="Upgrade current tariff.\n\n"
                            "Now users can only upgrade from Lite Match to Business Match.\n\n"
                            "If user is on tariff other than Lite Match, then status 403 will be returned.\n\n"
                            "If user tries to upgrade to tariff other than Business Match, "
                            "then status 400 will be returned.\n\n"
                            "Authenticated brand only.",
                responses={200: SubscriptionSerializer}
            )
            def upgrade(self, request, *args, **kwargs):
                return super().upgrade(request, *args, **kwargs)

        return Fixed


class Fix2(OpenApiViewExtension):
    target_class = 'core.apps.payments.api.PromocodeRetrieveApiView'

    def view_replacement(self):
        @extend_schema(
            tags=['Promocodes'],
        )
        class Fixed(self.target_class):
            """
            Get promo code object by code.

            Use this to check if the code entered by the user is valid.

            \tdiscount: integer (%)

            Authenticated brand only.
            """
            pass

        return Fixed
