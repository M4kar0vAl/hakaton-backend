from rest_framework import serializers

from .models import Tariff


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        exclude = []


class TariffSubscribeSerializer(serializers.Serializer):
    token = serializers.CharField()
    tariff = serializers.PrimaryKeyRelatedField(queryset=Tariff.objects.all())
    promocode = serializers.CharField(max_length=30, required=False)

    def create(self, validated_data):
        # TODO logic for creating payment object
        pass
