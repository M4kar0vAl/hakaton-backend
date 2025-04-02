from rest_framework import serializers

from core.apps.analytics.models import BrandActivity


class LogPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandActivity
        exclude = ['action']
        read_only_fields = ['brand', 'performed_at']

    def create(self, validated_data):
        brand = self.context['request'].user.brand

        instance = BrandActivity.objects.create(brand=brand, action=BrandActivity.PAYMENT)

        return instance
