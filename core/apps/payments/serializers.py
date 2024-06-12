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


class PaymentsSerializer(serializers.ModelSerializer):
    ...
