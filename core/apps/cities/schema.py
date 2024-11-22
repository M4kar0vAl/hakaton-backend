from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema


class Fix1(OpenApiViewExtension):
    target_class = 'core.apps.cities.api.CitiesListApiView'

    def view_replacement(self):
        @extend_schema(tags=['Cities'])
        class Fixed(self.target_class):
            """
            Get list of cities
            """
            pass

        return Fixed
