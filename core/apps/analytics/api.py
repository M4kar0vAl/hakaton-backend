from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.apps.analytics.models import BrandActivity
from core.apps.analytics.serializers import LogPaymentSerializer
from core.apps.brand.permissions import IsBrand


class BrandActivityViewSet(viewsets.GenericViewSet):
    queryset = BrandActivity.objects.all()
    serializer_class = LogPaymentSerializer
    permission_classes = [IsAuthenticated, IsBrand]

    @action(detail=False, methods=['POST'], url_name='log_payment')
    def log_payment(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data=serializer.data, status=status.HTTP_201_CREATED)
