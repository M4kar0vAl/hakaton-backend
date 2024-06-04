from rest_framework import serializers

from core.apps.brand.serializers import BrandGetSerializer
from core.apps.chat.models import Room, Message


class RoomSerializer(serializers.ModelSerializer):
    participants = BrandGetSerializer(many=True)

    class Meta:
        model = Room
        exclude = []


class MessageSerializer(serializers.ModelSerializer):
    user = BrandGetSerializer()
    room = RoomSerializer()

    class Meta:
        model = Message
        exclude = []
