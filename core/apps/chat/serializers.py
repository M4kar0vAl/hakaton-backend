from django.contrib.auth import get_user_model
from django.db import transaction, DatabaseError
from django.db.models import Prefetch, Subquery, OuterRef, Q, Max, F
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.apps.accounts.serializers import UserSerializer
from core.apps.brand.serializers import GetShortBrandSerializer
from core.apps.chat.exceptions import ServerError
from core.apps.chat.models import Room, Message, RoomFavorites, MessageAttachment
from core.apps.chat.utils import is_attachment_file_size_valid, is_attachment_file_type_valid

User = get_user_model()


class UserWithShortBrandSerializer(UserSerializer):
    brand = GetShortBrandSerializer(read_only=True)


class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        exclude = ['message', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Message
        exclude = []

    @extend_schema_field(MessageAttachmentSerializer(many=True))
    def get_attachments(self, message):
        return MessageAttachmentSerializer(message.attachments_objs, many=True).data


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        exclude = ['participants']


class RoomInterlocutorsMixin(serializers.Serializer):
    interlocutors = serializers.SerializerMethodField()

    @extend_schema_field(UserWithShortBrandSerializer(many=True))
    def get_interlocutors(self, room):
        # if room.type == Room.SUPPORT and not room.interlocutor_users:
        #     return W2W agency

        data = UserWithShortBrandSerializer(room.interlocutor_users, many=True).data

        return data


class RoomLastMessageMixin(serializers.Serializer):
    last_message = serializers.SerializerMethodField()

    @extend_schema_field(MessageSerializer)
    def get_last_message(self, room):
        if room.last_message:
            return MessageSerializer(room.last_message[0]).data

        return None


class RoomListSerializer(
    RoomSerializer,
    RoomInterlocutorsMixin,
    RoomLastMessageMixin
):
    pass


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
                ).prefetch_related(
                    Prefetch(
                        'attachments',
                        queryset=MessageAttachment.objects.all(),
                        to_attr='attachments_objs'
                    )
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


class MessageAttachmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        exclude = ['message', 'created_at']

    def validate_file(self, file):
        is_valid, max_size_mb = is_attachment_file_size_valid(file)

        if not is_valid:
            raise serializers.ValidationError(f'Uploaded file is too big! Max size is {max_size_mb} Mb.')

        if not is_attachment_file_type_valid(file):
            raise serializers.ValidationError(f'Uploaded file is of unsupported type!')

        return file

    def create(self, validated_data):
        file = validated_data.get('file')

        instance = MessageAttachment.objects.create(file=file)

        return instance
