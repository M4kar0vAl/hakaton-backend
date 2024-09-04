from rest_framework import serializers

from core.apps.accounts.serializers import UserSerializer
from core.apps.brand.serializers import BrandGetSerializer
from core.apps.chat.models import Room, Message


class RoomSerializer(serializers.ModelSerializer):
    # participants = BrandGetSerializer(many=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Room
        exclude = []

    def get_last_message(self, obj):
        return MessageSerializer(obj.messages.order_by('created_at').last()).data


class MessageSerializer(serializers.ModelSerializer):
    # user = UserSerializer()
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    class Meta:
        model = Message
        exclude = []
