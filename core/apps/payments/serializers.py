from dateutil.relativedelta import relativedelta
from django.db import transaction, DatabaseError
from django.utils import timezone
from rest_framework import serializers

from core.apps.payments.models import Tariff, PromoCode, Subscription


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        exclude = []


class TariffSubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        exclude = ['brand', 'upgraded_from', 'upgraded_at']
        read_only_fields = [
            'id', 'brand', 'start_date', 'end_date', 'is_active'
        ]
        extra_kwargs = {
            'promocode': {'required': False}
        }

    def to_representation(self, instance):
        obj = super().to_representation(instance)

        obj['tariff'] = TariffSerializer(instance.tariff).data

        return obj

    def validate(self, attrs):
        # check that user doesn't have active subscription
        if self.context['request'].user.brand.subscriptions.filter(
                is_active=True, end_date__gt=timezone.now()
        ).exists():
            raise serializers.ValidationError('You already have active subscription!')

        return attrs

    def create(self, validated_data):
        brand = self.context['request'].user.brand
        tariff = validated_data.get('tariff')
        promocode = validated_data.get('promocode')

        try:
            with transaction.atomic():
                # deactivate all expired active subscriptions
                # expired because this method not allowed if user has active, unexpired subscription
                brand.subscriptions.filter(is_active=True).update(is_active=False)

                now = timezone.now()

                if promocode:
                    if tariff.name == 'Trial':
                        subscription = Subscription.objects.create(
                            brand=brand,
                            tariff=tariff,
                            start_date=now,
                            end_date=now + tariff.duration,
                            is_active=True
                        )
                    else:
                        subscription = Subscription.objects.create(
                            brand=brand,
                            tariff=tariff,
                            start_date=now,
                            end_date=now + relativedelta(months=tariff.duration.days // 30),
                            is_active=True,
                            promocode=promocode
                        )
                else:
                    subscription = Subscription.objects.create(
                        brand=brand,
                        tariff=tariff,
                        start_date=now,
                        end_date=now + relativedelta(months=tariff.duration.days // 30),
                        is_active=True
                    )
        except DatabaseError:
            raise serializers.ValidationError("Failed to perform action! Please, try again.")

        return subscription


class TariffUpgradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        exclude = ['brand', 'upgraded_from', 'upgraded_at']
        read_only_fields = [
            'id', 'brand', 'start_date', 'end_date', 'is_active', 'promocode'
        ]

    def to_representation(self, instance):
        obj = super().to_representation(instance)

        obj['tariff'] = TariffSerializer(instance.tariff).data

        return obj

    def validate_tariff(self, tariff):
        if tariff.name != 'Business Match':
            raise serializers.ValidationError(f'You cannot upgrade to tariff: {tariff.name}')

        return tariff

    def update(self, instance, validated_data):
        tariff = validated_data.get('tariff')

        instance.upgraded_from_id = instance.tariff_id
        instance.upgraded_at = timezone.now()
        instance.tariff = tariff

        instance.save()

        return instance


class PromocodeGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        exclude = ['expires_at']
        read_only_fields = ['id', 'discount']


class SubscriptionSerializer(serializers.ModelSerializer):
    tariff = TariffSerializer()

    class Meta:
        model = Subscription
        exclude = ['brand', 'upgraded_from', 'upgraded_at']
