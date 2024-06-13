from datetime import datetime

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
    lookup_field = 'pk'

    def get_serializer_class(self):
        # if self.action == 'subscribe':
        #     return PaymentsSerializer

        return super().get_serializer_class()

    @action(methods=["POST"], detail=False)
    def subscribe(self, pk: int) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        serializer.is_valid(raise_exception=True)

        brand = self.request.user.user_set
        brand.subscription = instance
        brand.sub_expire = datetime.now() + instance.duration
        brand.save()
        return Response(data=serializer.data, status=200)
