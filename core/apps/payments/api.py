from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.apps.brand.permissions import IsBrand
from core.apps.payments.models import Tariff
from core.apps.payments.serializers import TariffSerializer, TariffSubscribeSerializer


class TariffViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Tariff.objects.all()
    serializer_class = TariffSerializer

    def get_permissions(self):
        if self.action == 'subscribe':
            permission_classes = [IsAuthenticated, IsBrand]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'subscribe':
            return TariffSubscribeSerializer

        return super().get_serializer_class()

    @action(methods=["POST"], detail=False, url_name='tariff_subscribe')
    def subscribe(self, request, *args, **kwargs) -> Response:
        # TODO logic for this method
        pass
