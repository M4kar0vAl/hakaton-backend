from rest_framework import serializers, exceptions

from .models import Subscription, PromoCode


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            'id',
            'name',
            'cost',
            'duration',
        ]


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ['code']


class PaymentsSerializer(serializers.Serializer):
    sub = serializers.IntegerField()
    promocode = serializers.CharField(required=False)

    def validate(self, attrs):
        try:
            self.instance = Subscription.objects.get(pk=attrs['sub'])
        except Subscription.DoesNotExist:
            raise exceptions.ValidationError(
                {'sub': f'Incorrect sub id: {attrs["sub"]}'},
                'invalid_subscription'
            )

        if attrs.get('promocode'):
            try:
                promocode = PromoCode.objects.get(code=attrs['promocode'])
            except PromoCode.DoesNotExist:
                raise exceptions.ValidationError(
                    {'promocode': f'Incorrect promocode: {attrs["promocode"]}'},
                    'invalid_promocode'
                )
            discount_multiplier = 1 - (promocode.discount) / 100
            self.instance.cost *= discount_multiplier
        return attrs
