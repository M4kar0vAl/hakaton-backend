from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.apps.articles.models import Tutorial
from core.apps.articles.permissions import IsStaff
from core.apps.articles.serializers import (
    ArticleFileCreateSerializer,
    TutorialListSerializer,
    TutorialRetrieveSerializer
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


class TutorialViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin
):
    queryset = Tutorial.objects.filter(is_published=True)
    serializer_class = TutorialListSerializer
    permission_classes = [IsAuthenticated, IsBrand, HasActiveSub]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TutorialRetrieveSerializer

        return super().get_serializer_class()
