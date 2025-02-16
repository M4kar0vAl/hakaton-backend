from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from core.apps.brand.utils import get_schema_standard_pagination_parameters
from core.apps.chat.serializers import RoomFavoritesListSerializer


class Fix1(OpenApiViewExtension):
    target_class = 'core.apps.chat.api.RoomFavoritesViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Chat'])
        class Fixed(self.target_class):
            @extend_schema(
                description='Get a list of favorite rooms.\n\n'
                            'Authenticated only.',
                parameters=[] + get_schema_standard_pagination_parameters()
            )
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

            @extend_schema(
                description='Add room to favorites.\n\n'
                            '\troom: id of a room to mark as favorite\n\n'
                            'Authenticated only.',
                responses={201: RoomFavoritesListSerializer}
            )
            def create(self, request, *args, **kwargs):
                return super().create(request, *args, **kwargs)

            @extend_schema(
                description='Remove room from favorites.\n\n'
                            'Authenticated only.',
                parameters=[
                    OpenApiParameter(
                        'id',
                        OpenApiTypes.INT,
                        OpenApiParameter.PATH,
                        many=False,
                        required=True,
                        description='Id of a RoomFavorites instance'
                    )
                ]
            )
            def destroy(self, request, *args, **kwargs):
                return super().destroy(request, *args, **kwargs)

        return Fixed
