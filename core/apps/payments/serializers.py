from rest_framework import serializers, exceptions

from .models import Tariff, UserSubscription, PromoCode


# Сериализатор Тарифа
class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = [
            'id',
            'name',
            'cost',
            'duration',
        ]


# Сериализатор Подписки
class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscription
        fields = [
            'user',
            'tariff',
            'is_active',
            'start_date',
            'end_date',
        ]


# class PaymentsSerializer(serializers.Serializer):
#     sub = serializers.IntegerField()
#     promocode = serializers.CharField(required=False)

#     def validate(self, attrs):
#         try:
#             self.instance = Subscription.objects.get(pk=attrs['sub'])
#         except Subscription.DoesNotExist:
#             raise exceptions.ValidationError(
#                 {'sub': f'Incorrect sub id: {attrs["sub"]}'},
#                 'invalid_subscription'
#             )

#         if attrs.get('promocode'):
#             try:
#                 promocode = PromoCode.objects.get(code=attrs['promocode'])
#             except PromoCode.DoesNotExist:
#                 raise exceptions.ValidationError(
#                     {'promocode': f'Incorrect promocode: {attrs["promocode"]}'},
#                     'invalid_promocode'
#                 )
#             discount_multiplier = 1 - (promocode.discount) / 100
#             self.instance.cost *= discount_multiplier
#         return attrs
