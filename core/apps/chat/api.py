from django.contrib.auth import get_user_model
from django.db.models import Subquery, OuterRef, Prefetch, Q, Max, F
from rest_framework import viewsets, mixins, generics
from rest_framework.permissions import IsAuthenticated

from core.apps.brand.pagination import StandardResultsSetPagination
from core.apps.brand.permissions import IsBrand
from core.apps.chat.models import Message, MessageAttachment
from core.apps.chat.permissions import IsOwnerOfRoomFavorite
from core.apps.chat.serializers import (
    RoomFavoritesListSerializer,
    RoomFavoritesCreateSerializer,
    MessageAttachmentCreateSerializer
)
from core.apps.payments.permissions import HasActiveSub

User = get_user_model()


class RoomFavoritesViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = RoomFavoritesListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.action == 'list':
            last_message_in_room = Message.objects.filter(
                pk=Subquery(Message.objects.filter(room=OuterRef('room')).order_by('-created_at').values('pk')[:1])
            ).prefetch_related(
                Prefetch(
                    'attachments',
                    queryset=MessageAttachment.objects.all(),
                    to_attr='attachments_objs'
                )
            )

            return self.request.user.room_favorites.select_related('room').prefetch_related(
                Prefetch(
                    'room__participants',
                    queryset=User.objects.filter(~Q(pk=self.request.user.id)).select_related('brand__category'),
                    to_attr='interlocutor_users'
                ),
                Prefetch(
                    'room__messages',
                    queryset=last_message_in_room,
                    to_attr='last_message'
                )
            ).annotate(
                last_message_created_at=Max('room__messages__created_at')
            ).order_by(
                F('last_message_created_at').desc(nulls_last=True)
            )

        return self.request.user.room_favorites.all()

    def get_permissions(self):
        permission_classes = self.permission_classes

        if self.action == 'destroy':
            permission_classes += [IsOwnerOfRoomFavorite]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return RoomFavoritesCreateSerializer

        return super().get_serializer_class()


class MessageAttachmentCreateView(generics.CreateAPIView):
    serializer_class = MessageAttachmentCreateSerializer
    permission_classes = [IsAuthenticated, IsBrand, HasActiveSub]

    def get_permissions(self):
        permission_classes = self.permission_classes
        user = self.request.user

        if user.is_staff or user.is_superuser:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]
