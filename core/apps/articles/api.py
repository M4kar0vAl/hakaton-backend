from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.apps.articles.models import Tutorial, CommunityArticle, MediaArticle, NewsArticle
from core.apps.articles.permissions import IsStaff
from core.apps.articles.serializers import (
    ArticleFileCreateSerializer,
    TutorialListSerializer,
    TutorialRetrieveSerializer,
    CommunityArticleListSerializer,
    CommunityArticleRetrieveSerializer,
    MediaArticleListSerializer,
    MediaArticleRetrieveSerializer,
    NewsArticleListSerializer,
    NewsArticleRetrieveSerializer
)
from core.apps.brand.permissions import IsBrand
from core.apps.payments.permissions import HasActiveSub


@extend_schema(exclude=True)
class ArticleFileUploadView(generics.CreateAPIView):
    serializer_class = ArticleFileCreateSerializer
    permission_classes = [IsStaff]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data={'location': serializer.data['file']}, status=status.HTTP_201_CREATED)


class BaseArticleViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin
):
    permission_classes = [IsAuthenticated, IsBrand, HasActiveSub]


class TutorialViewSet(BaseArticleViewSet):
    queryset = Tutorial.objects.filter(is_published=True)
    serializer_class = TutorialListSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TutorialRetrieveSerializer

        return super().get_serializer_class()


class CommunityArticleViewSet(BaseArticleViewSet):
    queryset = CommunityArticle.objects.filter(is_published=True)
    serializer_class = CommunityArticleListSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CommunityArticleRetrieveSerializer

        return super().get_serializer_class()


class MediaArticleViewSet(BaseArticleViewSet):
    queryset = MediaArticle.objects.filter(is_published=True)
    serializer_class = MediaArticleListSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MediaArticleRetrieveSerializer

        return super().get_serializer_class()


class NewsArticleViewSet(BaseArticleViewSet):
    queryset = NewsArticle.objects.filter(is_published=True)
    serializer_class = NewsArticleListSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return NewsArticleRetrieveSerializer

        return super().get_serializer_class()
