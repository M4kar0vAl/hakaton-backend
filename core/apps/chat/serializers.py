from django.contrib.auth import get_user_model
from django.db import transaction, DatabaseError
from django.db.models import Prefetch, Subquery, OuterRef, Q, Max, F
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.apps.accounts.serializers import UserSerializer
from core.apps.brand.serializers import GetShortBrandSerializer
from core.apps.chat.exceptions import ServerError
from core.apps.chat.models import Room, Message, RoomFavorites

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        exclude = []


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

    @extend_schema_field(MessageSerializer)
    def get_last_message(self, room):
        if room.last_message:
            return MessageSerializer(room.last_message[0]).data

        return None

    @extend_schema_field(GetShortBrandSerializer)
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


class RoomFavoritesListSerializer(serializers.ModelSerializer):
    room = RoomListSerializer()

    class Meta:
        model = RoomFavorites
        exclude = ['user']


class RoomFavoritesCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomFavorites
        exclude = ['user']

    def to_representation(self, instance):
        room = self.context['room_with_prefetched']

        obj = super().to_representation(instance)
        obj['room'] = RoomListSerializer(room).data

        return obj

    def validate(self, attrs):
        user = self.context['request'].user
        room = attrs.get('room')

        if user.room_favorites.filter(room=room).exists():
            raise serializers.ValidationError('You have already added this room to favorites!')

        attrs['user'] = user

        return attrs

    def create(self, validated_data):
        room = validated_data.get('room')
        user = validated_data.get('user')

        try:
            with transaction.atomic():
                # create RoomFavorites instance
                instance = RoomFavorites.objects.create(user=user, room=room)

                last_message_in_room = Message.objects.filter(
                    pk=Subquery(Message.objects.filter(room=OuterRef('room')).order_by('-created_at').values('pk')[:1])
                )

                # get instance's room with prefetched interlocutor and last message for to_representation method
                room_with_prefetched = Room.objects.filter(pk=room.pk).prefetch_related(
                    Prefetch(
                        'participants',
                        queryset=User.objects.filter(~Q(pk=user.id)).select_related('brand__category'),
                        to_attr='interlocutor_users'
                    ),
                    Prefetch(
                        'messages',
                        queryset=last_message_in_room,
                        to_attr='last_message'
                    )
                ).annotate(
                    last_message_created_at=Max('messages__created_at')
                ).order_by(
                    F('last_message_created_at').desc(nulls_last=True)
                ).get()

                # pass room with extra data to to_representation method using context
                self.context['room_with_prefetched'] = room_with_prefetched
        except DatabaseError:
            raise ServerError('Failed to perform action. Please, try again.')

        return instance
