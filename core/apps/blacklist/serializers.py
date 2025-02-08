from rest_framework import serializers

from core.apps.blacklist.models import BlackList
from core.apps.brand.serializers import GetShortBrandSerializer


class BlacklistListSerializer(serializers.ModelSerializer):
    blocked = GetShortBrandSerializer()

    class Meta:
        model = BlackList
        exclude = ['initiator']


class BlacklistCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlackList
        exclude = ['initiator']
        read_only_fields = ['id']

    def to_representation(self, instance):
        obj = super().to_representation(instance)
        obj['blocked'] = GetShortBrandSerializer(instance.blocked).data

        return obj

    def validate(self, attrs):
        initiator = self.context['request'].user.brand
        blocked = attrs.get('blocked')

        if initiator.id == blocked.id:
            raise serializers.ValidationError('You cannot block yourself.')

        if initiator.blacklist_as_initiator.filter(blocked=blocked).exists():
            raise serializers.ValidationError('You have already blocked this brand.')

        attrs['initiator'] = initiator

        return attrs

    def create(self, validated_data):
        initiator = validated_data.get('initiator')
        blocked = validated_data.get('blocked')

        instance = BlackList.objects.create(initiator=initiator, blocked=blocked)

        return instance
