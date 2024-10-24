import json
import os
import shutil

from django.conf import settings
from django.db import transaction, DatabaseError
from django.db.models import Q
from django.http import QueryDict
from rest_framework import viewsets, status, generics, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from core.apps.analytics.models import BrandActivity
from core.apps.analytics.utils import log_brand_activity
from core.apps.brand.models import Brand, Category, Format, Goal, ProductPhoto, GalleryPhoto, Tag, BusinessGroup
from core.apps.brand.permissions import IsOwnerOrReadOnly, IsBusinessSub, IsBrand
from core.apps.brand.serializers import (
    QuestionnaireChoicesSerializer,
    BrandCreateSerializer,
    BrandGetSerializer,
    MatchSerializer,
    InstantCoopSerializer, BrandUpdateSerializer,
)
from core.apps.chat.models import Room


class QuestionnaireChoicesListView(generics.GenericAPIView):
    """
    Api method to get answer choices for questionnaire choices questions.
    """
    serializer_class = QuestionnaireChoicesSerializer

    def get(self, request, *args, **kwargs):
        categories = Category.objects.filter(is_other=False)
        tags = Tag.objects.filter(is_other=False)
        formats = Format.objects.filter(is_other=False)
        goals = Goal.objects.filter(is_other=False)

        serializer = self.get_serializer({
            'categories': categories,
            'tags': tags,
            'formats': formats,
            'goals': goals
        })

        return Response(data=serializer.data, status=status.HTTP_200_OK)


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandGetSerializer
    http_method_names = [
        "get",
        "post",
        "patch",
        "delete",
        "head",
        "options",
        "trace",
    ]  # remove put from allowed methods

    def get_serializer_class(self):
        if self.action == 'create':
            return BrandCreateSerializer
        elif self.action == 'partial_update':
            return BrandUpdateSerializer
        elif self.action == 'like':
            return MatchSerializer
        elif self.action == 'instant_coop':
            return InstantCoopSerializer

        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'instant_coop':
            context['target_id'] = context['request'].data.get('target')

        return context

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action in ('partial_update', 'destroy'):
            permission_classes = [IsOwnerOrReadOnly]
        elif self.action == 'like':
            permission_classes = [IsAuthenticated, IsBrand]
        elif self.action == 'instant_coop':
            permission_classes = [IsAuthenticated, IsBrand, IsBusinessSub]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def transform_request_data(self, data):
        """
        Transform request data to support nested objects with multipart/form-data
        Nested objects should be sent as json string
        """
        force_dict_data = data
        if isinstance(force_dict_data, QueryDict):
            force_dict_data = force_dict_data.dict()

            # populate transformed data with all values of a multiple photos fields using QueryDict.getlist()
            # otherwise only last photo of the list will be taken
            for field in (
                    'product_photos_match', 'product_photos_card', 'gallery_photos_list', 'gallery_add'
            ):
                if field in data:
                    force_dict_data.update({
                        field: data.getlist(field)
                    })

        # transform JSON string to dictionary for each many field
        serializer = self.get_serializer()

        # key - field name, value - field instance
        for key, value in serializer.get_fields().items():
            if (
                isinstance(value, serializers.ListSerializer)  # ModelSerializer with many=True
                or isinstance(value, serializers.ModelSerializer)  # ModelSerializer
                or isinstance(value, serializers.ListField)  # ListField
                or isinstance(value, serializers.Serializer)  # non-model serializer
            ):
                # if key in data and value of this key is string, it means that this string is JSON string
                if key in force_dict_data and isinstance(force_dict_data[key], str):
                    if force_dict_data[key] == '':
                        force_dict_data[key] = None
                    else:
                        try:
                            force_dict_data[key] = json.loads(force_dict_data[key])
                        except Exception:
                            pass
        return force_dict_data

    def create(self, request, *args, **kwargs):
        transformed_data = self.transform_request_data(request.data)
        serializer = self.get_serializer(data=transformed_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def partial_update(self, request, *args, **kwargs):
        transformed_data = self.transform_request_data(request.data)
        instance = Brand.objects.select_related(
            'user',
            'category',
            'target_audience__age',
            'target_audience__gender'
        ).get(pk=kwargs['pk'])
        serializer = self.get_serializer(instance, data=transformed_data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(data=serializer.data, status=status.HTTP_200_OK)

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

                ProductPhoto.objects.filter(brand=instance).delete()
                GalleryPhoto.objects.filter(brand=instance).delete()
                BusinessGroup.objects.filter(brand=instance).delete()

                # ---remove fields that are no value for analytics---
                for field in [
                    'subscription',
                    'sub_expire'
                ]:
                    setattr(instance, field, None)

                for field in [
                    'logo',
                    'photo',
                    'tg_nickname',
                    'blog_url',
                    'inst_url',
                    'vk_url',
                    'tg_url',
                    'wb_url',
                    'lamoda_url',
                    'site_url',
                    'uniqueness',
                    'description',
                    'mission_statement',
                    'offline_space',
                    'problem_solving'
                ]:
                    setattr(instance, field, '')

                instance.save()
                # ---------------------------------------------------

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
