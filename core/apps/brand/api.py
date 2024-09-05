from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from core.apps.brand.models import Brand
from core.apps.brand.permissions import IsOwnerOrReadOnly, IsBusinessSub, IsBrand
from core.apps.brand.serializers import (
    BrandCreateSerializer,
    BrandGetSerializer,
    MatchSerializer,
    InstantCoopSerializer,
)


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandGetSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return BrandCreateSerializer
        elif self.action == 'like':
            return MatchSerializer
        elif self.action == 'instant_coop':
            return InstantCoopSerializer

        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'instant_coop':
            context['target_id'] = context['request'].data.get('target')

        return context

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action in ('update', 'partial_update', 'destroy'):
            permission_classes = [IsOwnerOrReadOnly]
        elif self.action == 'like':
            permission_classes = [IsAuthenticated, IsBrand]
        elif self.action == 'instant_coop':
            permission_classes = [IsAuthenticated, IsBrand, IsBusinessSub]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'])
    def like(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def instant_coop(self, request):
        """
        Instant cooperation.
        Returns room instance.

        Only one cooperation room per a pair of brands. No matter who were the initiator.
        If room already exists, will raise BadRequest exception (400) and return error text with existing room id.

        Business subscription only.
        """
        serializer = self.get_serializer(data={})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)
