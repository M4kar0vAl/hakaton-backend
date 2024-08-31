from datetime import datetime
import json

from rest_framework import viewsets, mixins, generics
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_201_CREATED, HTTP_200_OK

from yookassa import Configuration, Payment as YooPayment

from core.apps.payments.models import Tariff, UserSubscription
from core.apps.payments.serializers import TariffSerializer
from core.config import settings

class CreatePaymentView(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        tariff_id = request.data.get('tariff_id')

        try:
            tariff = Tariff.objects.get(id=tariff_id)
        except Tariff.DoesNotExist:
            return Response({'error': 'Invalid tariff id'},
                            status=HTTP_400_BAD_REQUEST)

        Configuration.account_id = settings.YOOKASSA_ACCOUNT_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

        user_subscription = UserSubscription.objects.create(
            user=user,
            tariff=tariff,
            is_active=False,
        )

        payment = YooPayment.create({
            "amount": {
                "value": str(tariff.price),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": settings.YOOKASSA_RETURN_URL
            },
            "capture": True,
            "description": f"Оплата подписки {tariff.name} пользователем {user.email}",
            "metadata": {
                "user_subscription_id": user_subscription.id,
            }
        })

        return Response({
            "id": payment.id,
            "status": payment.status,
            "confirmation_url": payment.confirmation.confirmation_url
        }, status=HTTP_201_CREATED)


class TariffListView(generics.ListAPIView):
    queryset = Tariff.objects.all()
    serializer_class = TariffSerializer


@api_view(['POST'])
def payment_webhook(request):
    data = json.loads(request.body)
    # https://yookassa.ru/developers/using-api/webhooks#using
    if 'event' in data and 'object' in data:
        event = data['event']
        object = data['object']

        if event == 'payment.succeeded':
            try:
                user_subscription = UserSubscription.objects.get(
                    id=object['metadata']['user_subscription_id']
                    )
                user_subscription.activate()
            except UserSubscription.DoesNotExist:
                return Response({'error': "User's subscription not found"},status=HTTP_400_BAD_REQUEST)
        return Response({'status': 'ok'}, status=HTTP_200_OK)
    else:
        return Response({'error': 'Invalid data'}, status=HTTP_400_BAD_REQUEST)

# class PaymentViewSet(
#     mixins.ListModelMixin,
#     viewsets.GenericViewSet,
# ):
#     queryset = Subscription.objects.all()
#     serializer_class = SubscriptionSerializer

#     def get_permissions(self):
#         if self.action == 'subscribe':
#             return [IsAuthenticated(), ]

#         return super().get_permissions()

#     def get_serializer_class(self):
#         if self.action == 'subscribe':
#             return PaymentsSerializer

#         return super().get_serializer_class()

#     @action(methods=["POST"], detail=False, url_name='subscription')
#     def subscribe(self, request, *args, **kwargs) -> Response:
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         sub = serializer.instance
#         brand = self.request.user.brand
#         brand.subscription = sub
#         brand.sub_expire = datetime.now() + sub.duration
#         brand.save()

#         return Response(data=SubscriptionSerializer(sub).data, status=200)
