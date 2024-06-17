from datetime import datetime

from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Subscription
from .permissions import IsAuthenticated
from .serializers import SubscriptionSerializer, PaymentsSerializer


class PaymentViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer

    def get_permissions(self):
        if self.action == 'subscribe':
            return [IsAuthenticated(), ]

        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'subscribe':
            return PaymentsSerializer

        return super().get_serializer_class()

    @action(methods=["POST"], detail=False, url_name='subscription')
    def subscribe(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sub = serializer.instance
        brand = self.request.user.brand
        brand.subscription = sub
        brand.sub_expire = datetime.now() + sub.duration
        brand.save()

        return Response(data=SubscriptionSerializer(sub).data, status=200)
