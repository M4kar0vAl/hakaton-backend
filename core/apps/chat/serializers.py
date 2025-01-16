from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.apps.accounts.serializers import UserSerializer
from core.apps.brand.serializers import GetShortBrandSerializer
from core.apps.chat.models import Room, Message


User = get_user_model()


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
        # if room.type == Room.SUPPORT and not room.interlocutor_users:
        #     return W2W agency

        users = []
        brands = []

        # interlocutor_users is a list of users in the room who are not the current user
        for user in room.interlocutor_users:
            try:
                brand = user.brand
                brands.append(brand)
            except User.brand.RelatedObjectDoesNotExist:
                # users without brands are admins
                users.append(user)

        data = []

        if users:
            data += UserSerializer(users, many=True).data

        if brands:
            data += GetShortBrandSerializer(brands, many=True).data

        return data


class MessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Message
        exclude = []
