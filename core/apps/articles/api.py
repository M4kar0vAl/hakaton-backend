from rest_framework import generics, status
from rest_framework.response import Response

from core.apps.articles.permissions import IsStaff
from core.apps.articles.serializers import ArticleFileCreateSerializer


class ArticleFileUploadView(generics.CreateAPIView):
    serializer_class = ArticleFileCreateSerializer
    permission_classes = [IsStaff]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data={'location': serializer.data['file']}, status=status.HTTP_201_CREATED)
