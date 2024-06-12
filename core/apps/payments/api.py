from rest_framework import viewsets, mixins
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Subscription
from .serializers import SubscriptionSerializer, PaymentsSerializer


class PaymentViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        if self.action == 'subscribe':
            return PaymentsSerializer

        return super().get_serializer_class()

    @action(methods=["POST"], detail=False)
    def subscribe(self, sub: int) -> Response:
        ...
