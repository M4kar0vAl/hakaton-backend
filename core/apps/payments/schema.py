from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema


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
                description=""
            )
            def subscribe(self, request, *args, **kwargs):
                return super().subscribe(request, *args, **kwargs)

        return Fixed
