from dateutil.relativedelta import relativedelta
from django.db import transaction, DatabaseError
from django.utils import timezone
from rest_framework import serializers

from core.apps.payments.models import Tariff, PromoCode, Subscription, GiftPromoCode


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        exclude = []


class TariffSubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        exclude = ['brand', 'upgraded_from', 'upgraded_at', 'gift_promocode']
        read_only_fields = [
            'id', 'start_date', 'end_date', 'is_active'
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
        exclude = ['brand', 'upgraded_from', 'upgraded_at', 'gift_promocode']
        read_only_fields = [
            'id', 'start_date', 'end_date', 'is_active', 'promocode'
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
        exclude = ['brand', 'upgraded_from', 'upgraded_at', 'gift_promocode']


class GiftPromoCodeGetSerializer(serializers.ModelSerializer):
    tariff = TariffSerializer()

    class Meta:
        model = GiftPromoCode
        fields = ['id', 'code', 'expires_at', 'tariff']


class GiftPromoCodeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftPromoCode
        exclude = ['id', 'created_at', 'giver', 'is_used']
        read_only_fields = ['code', 'expires_at']
        extra_kwargs = {
            'tariff': {'write_only': True},
        }

    def validate(self, attrs):
        brand = self.context['request'].user.brand
        tariff = attrs.get('tariff')
        promocode = attrs.get('promocode')

        if tariff.name == 'Trial':
            raise serializers.ValidationError('You cannot gift trial tariff!')

        if promocode is not None:
            # check that promo code wasn't used when purchasing subscription
            if brand.subscriptions.filter(promocode=promocode).exists():
                raise serializers.ValidationError('You have already used this promocode!')

            # check that promo code wasn't used when purchasing a gift
            if brand.gifts_as_giver.filter(promocode=promocode).exists():
                raise serializers.ValidationError('You have already used this promocode!')

        return attrs

    def create(self, validated_data):
        tariff = validated_data.get('tariff')
        promocode = validated_data.get('promocode')

        brand = self.context['request'].user.brand
        expires_at = timezone.now() + relativedelta(months=6)

        gift_code = GiftPromoCode.objects.create(
            tariff=tariff,
            expires_at=expires_at,
            giver=brand,
            promocode=promocode
        )

        return gift_code


class GiftPromoCodeActivateSerializer(serializers.ModelSerializer):
    tariff = TariffSerializer(read_only=True)

    class Meta:
        model = Subscription
        exclude = ['brand', 'upgraded_from', 'upgraded_at']
        read_only_fields = [
            'id', 'start_date', 'end_date', 'is_active', 'promocode'
        ]
        extra_kwargs = {
            'gift_promocode': {'write_only': True}
        }

    def validate(self, attrs):
        cur_brand = self.context['request'].user.brand
        gift_promocode = attrs.get('gift_promocode')

        # check that cannot use own gift
        if gift_promocode.giver_id == cur_brand.id:
            raise serializers.ValidationError('You cannot use your own gift!')

        # check that gift hasn't expired yet
        if gift_promocode.expires_at <= timezone.now():
            raise serializers.ValidationError('Gift already expired!')

        # check that gift hasn't been used
        if gift_promocode.is_used:
            raise serializers.ValidationError('Gift has already been used!')

        # check that cannot activate if already has active subscription
        if cur_brand.subscriptions.filter(
                is_active=True, end_date__gt=timezone.now()
        ).exists():
            raise serializers.ValidationError('You already have active subscription!')

        return attrs

    def create(self, validated_data):
        gift_promocode = validated_data.get('gift_promocode')
        now = timezone.now()

        try:
            with transaction.atomic():
                brand = self.context['request'].user.brand
                tariff = gift_promocode.tariff

                # create subscription
                subscription = Subscription.objects.create(
                    brand=brand,
                    tariff=gift_promocode.tariff,
                    start_date=now,
                    end_date=now + relativedelta(months=tariff.duration.days // 30),
                    is_active=True,
                    gift_promocode=gift_promocode
                )

                # mark gift_promocode as used
                gift_promocode.is_used = True
                gift_promocode.save()
        except DatabaseError:
            raise serializers.ValidationError("Failed to perform action! Please, try again.")

        return subscription
