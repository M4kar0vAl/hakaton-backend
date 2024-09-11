import os
import shutil

from django.conf import settings
from django.db import transaction, DatabaseError
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from core.apps.analytics.models import BrandActivity
from core.apps.analytics.utils import log_brand_activity
from core.apps.brand.models import Brand
from core.apps.brand.permissions import IsOwnerOrReadOnly, IsBusinessSub, IsBrand
from core.apps.brand.serializers import (
    BrandCreateSerializer,
    BrandGetSerializer,
    MatchSerializer,
    InstantCoopSerializer,
    CollaborationSerializer,
)
from core.apps.chat.models import Room


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandGetSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return BrandCreateSerializer
        elif self.action == 'like':
            return MatchSerializer
        elif self.action == 'instant_coop':
            return InstantCoopSerializer
        elif self.action == 'report_collab':
            return CollaborationSerializer

        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'instant_coop':
            context['target_id'] = context['request'].data.get('target')

        return context

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action in ('update', 'partial_update', 'destroy'):
            permission_classes = [IsOwnerOrReadOnly]
        elif self.action in ('like', 'report_collab'):
            permission_classes = [IsAuthenticated, IsBrand]
        elif self.action == 'instant_coop':
            permission_classes = [IsAuthenticated, IsBrand, IsBusinessSub]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def perform_destroy(self, instance):
        user_id = instance.user.id  # need to get it here cuz it will be unavailable once the user is deleted
        try:
            with transaction.atomic():
                user = instance.user

                # delete user's support and help chats
                # messages in that chats will be deleted
                user.rooms.filter(Q(type=Room.SUPPORT) | Q(type=Room.HELP)).delete()

                # delete user, brand will remain with user=NULL
                # all user's messages 'user' field in match and instant chats will be set to NULL
                user.delete()

                # need to call this before calling instance.save(),
                # cuz instance think that 'user' field was changed to NULL (and wasn't saved)
                # and it doesn't know user was deleted
                instance.refresh_from_db()

                # remove images urls from DB
                instance.logo = None
                instance.photo = None
                instance.product_photo = None
                instance.subscription = None
                instance.sub_expire = None
                instance.save()

                # get path to 'deleted' user's media files directory (media/user_{user.id})
                path_to_user_dir = os.path.join(settings.MEDIA_ROOT, f'user_{user_id}')

                # delete user directory with all images in it
                try:
                    shutil.rmtree(path_to_user_dir)
                except FileNotFoundError:
                    # does nothing if directory was not found
                    pass

                log_brand_activity(brand=instance, action=BrandActivity.DELETION)
        except DatabaseError:
            return Response({'detail': 'Unexpected database error. Please try again.'})

    @action(detail=False, methods=['post'])
    def like(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def instant_coop(self, request):
        """
        Instant cooperation.
        Returns room instance.

        Only one cooperation room per a pair of brands. No matter who were the initiator.
        If room already exists, will raise BadRequest exception (400) and return error text with existing room id.

        Business subscription only.
        """
        serializer = self.get_serializer(data={})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def report_collab(self, request):
        """
        Report collaboration results of two brands.

        collab_with: id of brand with which collaborated.

        Returns collaboration instance.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)
