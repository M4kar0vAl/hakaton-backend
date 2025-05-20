from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema


class Fix1(OpenApiViewExtension):
    target_class = 'core.apps.articles.api.TutorialViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Tutorials'])
        class Fixed(self.target_class):
            @extend_schema(
                description="Get tutorials list.\n\n"
                            "Authenticated brand with active subscription only."
            )
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

            @extend_schema(
                description="Get tutorial body by ID.\n\n"
                            "\tcontent: HTML-string\n\n"
                            "Authenticated brand with active subscription only."
            )
            def retrieve(self, request, *args, **kwargs):
                return super().retrieve(request, *args, **kwargs)

        return Fixed


class Fix2(OpenApiViewExtension):
    target_class = 'core.apps.articles.api.CommunityArticleViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Community Articles'])
        class Fixed(self.target_class):
            @extend_schema(
                description="Get community articles list.\n\n"
                            "Authenticated brand with active subscription only."
            )
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

            @extend_schema(
                description="Get community article body by ID.\n\n"
                            "\tcontent: HTML-string\n\n"
                            "Authenticated brand with active subscription only."
            )
            def retrieve(self, request, *args, **kwargs):
                return super().retrieve(request, *args, **kwargs)

        return Fixed


class Fix3(OpenApiViewExtension):
    target_class = 'core.apps.articles.api.MediaArticleViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Media Articles'])
        class Fixed(self.target_class):
            @extend_schema(
                description="Get media articles list.\n\n"
                            "Authenticated brand with active subscription only."
            )
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

            @extend_schema(
                description="Get media article body by ID.\n\n"
                            "\tcontent: HTML-string\n\n"
                            "Authenticated brand with active subscription only."
            )
            def retrieve(self, request, *args, **kwargs):
                return super().retrieve(request, *args, **kwargs)

        return Fixed


class Fix4(OpenApiViewExtension):
    target_class = 'core.apps.articles.api.NewsArticleViewSet'

    def view_replacement(self):
        @extend_schema(tags=['News Articles'])
        class Fixed(self.target_class):
            @extend_schema(
                description="Get news articles list.\n\n"
                            "Authenticated brand with active subscription only."
            )
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

            @extend_schema(
                description="Get news article body by ID.\n\n"
                            "\tcontent: HTML-string\n\n"
                            "Authenticated brand with active subscription only."
            )
            def retrieve(self, request, *args, **kwargs):
                return super().retrieve(request, *args, **kwargs)

        return Fixed
