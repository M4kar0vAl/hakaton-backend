from django.db.models import Q
from rest_framework import serializers

from core.apps.brand.models import Brand
from core.apps.brand.serializers import GetShortBrandSerializer
from core.apps.chat.models import Room, Message


class RoomSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    interlocutors_brand = serializers.SerializerMethodField()

    class Meta:
        model = Room
        exclude = []

    def get_last_message(self, obj):
        return MessageSerializer(obj.messages.order_by('created_at').last()).data

    def get_interlocutors_brand(self, obj):
        if self.context['scope']['user'].is_staff:
            # admins are getting all participants brands if they have one
            return GetShortBrandSerializer(Brand.objects.filter(pk__in=obj.participants.all()), many=True).data
        else:
            try:
                # get interlocutor's brand
                return GetShortBrandSerializer(
                    Brand.objects.get(
                        user__pk__in=obj.participants.filter(
                            ~Q(pk=self.context['scope']['user'].pk)
                        ).values_list('pk', flat=True)
                    )
                ).data
            except Brand.DoesNotExist:
                return None  # this is only for support and help rooms OR if user was deleted. Maybe return W2W agency


class MessageSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    class Meta:
        model = Message
        exclude = []
