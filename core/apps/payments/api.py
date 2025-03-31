from django.utils import timezone
from rest_framework import viewsets, mixins, status, generics, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.apps.brand.permissions import IsBrand
from core.apps.payments.models import Tariff, PromoCode, GiftPromoCode
from core.apps.payments.permissions import CanUpgradeTariff, HasActiveSub
from core.apps.payments.serializers import (
    TariffSerializer,
    TariffSubscribeSerializer,
    PromocodeGetSerializer,
    TariffUpgradeSerializer,
    GiftPromoCodeGetSerializer,
    GiftPromoCodeCreateSerializer,
    GiftPromoCodeActivateSerializer
)


class TariffViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Tariff.objects.all()
    serializer_class = TariffSerializer

    def get_permissions(self):
        if self.action == 'subscribe':
            permission_classes = [IsAuthenticated, IsBrand]
        elif self.action == 'upgrade':
            permission_classes = [IsAuthenticated, IsBrand, CanUpgradeTariff]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'subscribe':
            return TariffSubscribeSerializer
        elif self.action == 'upgrade':
            return TariffUpgradeSerializer

        return super().get_serializer_class()

    @action(methods=["POST"], detail=False, url_name='subscribe')
    def subscribe(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['patch'], url_name='upgrade')
    def upgrade(self, request, *args, **kwargs):
        current_sub = request.user.brand.subscriptions.filter(
            is_active=True, end_date__gt=timezone.now()
        ).order_by('-id').first()

        serializer = self.get_serializer(current_sub, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data=serializer.data, status=status.HTTP_200_OK)


class PromocodeRetrieveApiView(generics.RetrieveAPIView):
    queryset = PromoCode.objects.filter(expires_at__gt=timezone.now())
    serializer_class = PromocodeGetSerializer
    permission_classes = [IsAuthenticated, IsBrand]
    lookup_field = 'code'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.is_used_by_brand(request.user.brand):
            raise serializers.ValidationError('You have already used this promocode!')

        serializer = self.get_serializer(instance)

        return Response(data=serializer.data, status=status.HTTP_200_OK)


class GiftPromoCodeViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    queryset = GiftPromoCode.objects.filter(is_used=False, expires_at__gt=timezone.now())
    serializer_class = GiftPromoCodeGetSerializer
    lookup_field = 'code'

    def get_queryset(self):
        if self.action == 'list':
            # return unused and unexpired gift promo codes purchased by the current brand
            return self.request.user.brand.gifts_as_giver.filter(is_used=False, expires_at__gt=timezone.now())
        return super().get_queryset()

    def get_permissions(self):
        permission_classes = [IsAuthenticated, IsBrand]

        if self.action == 'create':
            permission_classes += [HasActiveSub]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return GiftPromoCodeCreateSerializer
        elif self.action == 'activate':
            return GiftPromoCodeActivateSerializer

        return super().get_serializer_class()

    def retrieve(self, request, *args, **kwargs):
        gift_code = self.get_object()

        serializer = self.get_serializer(gift_code)

        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_name='activate')
    def activate(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data=serializer.data, status=status.HTTP_201_CREATED)
