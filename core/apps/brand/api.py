from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from core.apps.brand.models import Brand
from core.apps.brand.permissions import IsOwnerOrReadOnly
from core.apps.brand.serializers import BrandCreateSerializer, BrandGetSerializer, MatchSerializer


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandGetSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return BrandCreateSerializer
        elif self.action == 'like':
            return MatchSerializer

        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ('create', 'like'):
            permission_classes = [IsAuthenticated]
        elif self.action in ('update', 'partial_update', 'destroy'):
            permission_classes = [IsOwnerOrReadOnly]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['post'])
    def like(self, request, brand_pk):
        current_brand = self.get_object()
        match = current_brand.like(brand_pk)
        serializer = self.get_serializer_class()(match)
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.data, status=200)
