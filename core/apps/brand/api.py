from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny

from core.apps.brand.models import Brand
from core.apps.brand.permissions import IsOwnerOrReadOnly
from core.apps.brand.serializers import BrandCreateSerializer, BrandGetSerializer


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandGetSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return BrandCreateSerializer

        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action in ('update', 'partial_update', 'destroy'):
            permission_classes = [IsOwnerOrReadOnly]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
