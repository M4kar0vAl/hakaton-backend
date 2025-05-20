from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from core.apps.blacklist.serializers import BlacklistListSerializer
from core.apps.brand.utils import get_schema_standard_pagination_parameters


class Fix1(OpenApiViewExtension):
    target_class = 'core.apps.blacklist.api.BlacklistViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Blacklist'])
        class Fixed(self.target_class):
            @extend_schema(
                description='Get a list of blocked brands.\n\n'
                            'Authenticated brand with active subscription only.',
                parameters=[] + get_schema_standard_pagination_parameters()
            )
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

            @extend_schema(
                description='Add brand to blacklist.\n\n'
                            '\tblocked: id of a brand to block\n\n'
                            'Authenticated brand with active subscription only.',
                responses={201: BlacklistListSerializer}
            )
            def create(self, request, *args, **kwargs):
                return super().create(request, *args, **kwargs)

            @extend_schema(
                description='Remove brand from blacklist.\n\n'
                            'Authenticated brand with active subscription only.',
                parameters=[
                    OpenApiParameter(
                        'id',
                        OpenApiTypes.INT,
                        OpenApiParameter.PATH,
                        many=False,
                        required=True,
                        description='Id of a Blacklist instance'
                    )
                ]
            )
            def destroy(self, request, *args, **kwargs):
                return super().destroy(request, *args, **kwargs)

        return Fixed
