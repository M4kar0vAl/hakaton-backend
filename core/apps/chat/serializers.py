from rest_framework import serializers

from core.apps.brand.serializers import GetShortBrandSerializer
from core.apps.chat.models import Room, Message


class RoomSerializer(serializers.ModelSerializer):

    class Meta:
        model = Room
        exclude = ['participants']


class RoomListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    interlocutors_brand = serializers.SerializerMethodField()

    class Meta:
        model = Room
        exclude = ['participants']

    def get_last_message(self, room):
        if room.last_message:
            return MessageSerializer(room.last_message[0]).data

        return None

    def get_interlocutors_brand(self, room):
        # if self.context['scope']['user'].is_staff:
        #     return GetShortBrandSerializer((user.brand for user in obj.interlocutor_users), many=True).data
        # else:
        #     if obj.type == Room.SUPPORT:
        #         return W2W agency
        #     else:
        #         return GetShortBrandSerializer((user.brand for user in obj.interlocutor_users), many=True).data

        # obj.interlocutor_users is a list of users in the room which are not the current user
        return GetShortBrandSerializer((user.brand for user in room.interlocutor_users), many=True).data


class MessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Message
        exclude = []
