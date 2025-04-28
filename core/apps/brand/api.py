import json
import os
import shutil

from django.conf import settings
from django.db import transaction, DatabaseError
from django.db.models import Q, Subquery, Prefetch, Value, Count, OuterRef
from django.http import QueryDict
from rest_framework import viewsets, status, generics, serializers, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.apps.analytics.models import BrandActivity
from core.apps.analytics.utils import log_brand_activity
from core.apps.blacklist.models import BlackList
from core.apps.brand.models import (
    Brand,
    Category,
    Format,
    Goal,
    ProductPhoto,
    GalleryPhoto,
    Tag,
    BusinessGroup,
    Blog,
    Match
)
from core.apps.brand.pagination import StandardResultsSetPagination
from core.apps.brand.permissions import IsBrand, CanInstantCoop, IsNotCurrentBrand, NotInBlacklistOfTarget, \
    DidNotBlockTarget
from core.apps.brand.serializers import (
    QuestionnaireChoicesSerializer,
    BrandCreateSerializer,
    BrandGetSerializer,
    MatchSerializer,
    InstantCoopSerializer,
    BrandUpdateSerializer,
    CollaborationSerializer,
    LikedBySerializer,
    MyLikesSerializer,
    MyMatchesSerializer,
    RecommendedBrandsSerializer,
    BrandMeSerializer,
    StatisticsSerializer,
)
from core.apps.brand.utils import get_statistics_list, get_recommended_brands
from core.apps.chat.models import Room
from core.apps.payments.models import Subscription
from core.apps.payments.permissions import HasActiveSub, IsBusinessSub


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


class BrandViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Brand.objects.filter(user__isnull=False)  # if user is null, then brand was deleted
    serializer_class = BrandGetSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.action == 'liked_by':
            current_brand = self.request.user.brand

            # get all brands that current brand added to its blacklist
            blocked_brands = current_brand.blacklist_as_initiator.values_list('blocked', flat=True)

            # get all brands that added the current one to the blacklist
            blocked_by = current_brand.blacklist_as_blocked.values_list('initiator', flat=True)

            # get ids of all brands which liked current one and haven't been liked in response yet
            liked_by_ids = current_brand.target.filter(
                is_match=False
            ).exclude(
                Q(initiator__in=blocked_brands)
                | Q(initiator__in=blocked_by)
            ).values_list('initiator', flat=True)

            # get time of each like
            like_at = Subquery(current_brand.target.filter(initiator=OuterRef('id')).values('like_at')[:1])

            return Brand.objects.filter(pk__in=Subquery(liked_by_ids)).annotate(like_at=like_at).order_by('-like_at')

        elif self.action == 'my_likes':
            current_brand = self.request.user.brand

            # get all brands that current brand added to its blacklist
            blocked_brands = current_brand.blacklist_as_initiator.values_list('blocked', flat=True)

            # get all brands that added the current one to the blacklist
            blocked_by = current_brand.blacklist_as_blocked.values_list('initiator', flat=True)

            # get ids of all brands that were liked by the current brand.
            my_likes_ids = current_brand.initiator.filter(
                is_match=False
            ).exclude(
                Q(target__in=blocked_brands)
                | Q(target__in=blocked_by)
            ).values_list('target', flat=True)

            # get time of each like
            like_at = Subquery(current_brand.initiator.filter(target=OuterRef('id')).values('like_at')[:1])

            # Prefetch product_photos of the CARD format to improve performance
            # and set them to a 'card_photos' attribute
            # prefetch instant rooms for the brand user
            return Brand.objects.filter(pk__in=Subquery(my_likes_ids)).select_related('user').prefetch_related(
                Prefetch(
                    'product_photos',
                    queryset=ProductPhoto.objects.filter(format=ProductPhoto.CARD),
                    to_attr='card_photos'
                ),
                Prefetch(
                    'user__rooms',
                    queryset=Room.objects.filter(type=Room.INSTANT),
                    to_attr='instant_rooms'
                )
            ).annotate(like_at=like_at).order_by('-like_at')

        elif self.action == 'my_matches':
            current_brand = self.request.user.brand

            # get ids of brands that have match with current brand as initiator
            my_matches_ids_as_initiator = current_brand.initiator.filter(
                is_match=True
            ).values_list('target', flat=True)

            # get ids of brands that have match with current brand as target
            my_matches_ids_as_target = current_brand.target.filter(
                is_match=True
            ).values_list('initiator', flat=True)

            match_at = Subquery(Match.objects.filter(
                Q(initiator=current_brand, target=OuterRef('id')) | Q(initiator=OuterRef('id'), target=current_brand),
                is_match=True
            ).values('match_at')[:1])

            # get all brands that have match with current brand
            # prefetch card photos and match rooms to improve performance
            return Brand.objects.filter(
                Q(pk__in=Subquery(my_matches_ids_as_initiator)) | Q(pk__in=Subquery(my_matches_ids_as_target))
            ).select_related('user').prefetch_related(
                Prefetch(
                    'product_photos',
                    queryset=ProductPhoto.objects.filter(format=ProductPhoto.CARD),
                    to_attr='card_photos'
                ),
                Prefetch(
                    'user__rooms',
                    queryset=Room.objects.filter(type=Room.MATCH),
                    to_attr='match_rooms'
                )
            ).annotate(match_at=match_at).order_by('-match_at')

        elif self.action == 'recommended_brands':
            avg_bill = self.request.query_params.get('avg_bill')
            subs_count = self.request.query_params.get('subs_count')
            categories_ids = self.request.query_params.getlist('category')
            cities_ids = self.request.query_params.getlist('city')

            current_brand = self.request.user.brand

            recommended_brands = get_recommended_brands(
                current_brand, avg_bill, subs_count, categories_ids, cities_ids
            )

            return recommended_brands

        elif self.action == 'statistics':
            current_brand = self.request.user.brand
            period: int = self.request.query_params.get('period')  # number of months

            if period is None:
                raise serializers.ValidationError('"period" must be specified')

            try:
                period = int(period)
            except ValueError:
                raise serializers.ValidationError(
                    f'{period} is not a valid period. Valid period is from range [1, 12] inclusive'
                )

            if period not in range(1, 13):
                raise serializers.ValidationError(
                    f'{period} is not a valid period. Valid period is from range [1, 12] inclusive'
                )

            results = get_statistics_list(current_brand, period)

            return results

        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'create':
            return BrandCreateSerializer
        elif self.action == 'me':
            if self.request.method == 'GET':
                return BrandMeSerializer
            elif self.request.method == 'PATCH':
                return BrandUpdateSerializer
        elif self.action == 'like':
            return MatchSerializer
        elif self.action == 'instant_coop':
            return InstantCoopSerializer
        elif self.action == 'liked_by':
            return LikedBySerializer
        elif self.action == 'my_likes':
            return MyLikesSerializer
        elif self.action == 'my_matches':
            return MyMatchesSerializer
        elif self.action == 'recommended_brands':
            return RecommendedBrandsSerializer
        elif self.action == 'statistics':
            return StatisticsSerializer

        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'instant_coop':
            context['target_id'] = context['request'].data.get('target')

        elif self.action == 'my_likes':
            # pass ids of current user's rooms
            # evaluate queryset here to avoid reevaluating it each time
            # self.context['current_user_instant_room_ids'] is called
            context['current_user_instant_rooms_ids'] = set(context['request'].user.rooms.filter(
                type=Room.INSTANT
            ).values_list('pk', flat=True))

        elif self.action == 'my_matches':
            context['current_user_match_rooms_ids'] = set(context['request'].user.rooms.filter(
                type=Room.MATCH
            ).values_list('pk', flat=True))

        return context

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action == 'retrieve':
            permission_classes = [IsAuthenticated, IsBrand, IsNotCurrentBrand, HasActiveSub, NotInBlacklistOfTarget]
        elif self.action == 'me':
            if self.request.method in ('GET', 'PATCH', 'DELETE'):
                permission_classes = [IsAuthenticated, IsBrand]
        elif self.action in ('like', 'liked_by', 'my_likes', 'my_matches', 'recommended_brands', 'statistics'):
            permission_classes = [IsAuthenticated, IsBrand, HasActiveSub]

            if self.action == 'like':
                permission_classes += [NotInBlacklistOfTarget, DidNotBlockTarget]
        elif self.action == 'instant_coop':
            permission_classes = [
                IsAuthenticated, IsBrand, IsBusinessSub, CanInstantCoop, NotInBlacklistOfTarget, DidNotBlockTarget
            ]
        else:
            permission_classes = [IsAuthenticated]
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
                    'product_photos_match', 'product_photos_card', 'gallery_photos_list', 'gallery_add',
                    'product_photos_match_add', 'product_photos_card_add'
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

    def perform_destroy(self, instance):
        user_id = instance.user.id  # need to get it here cuz it will be unavailable once the user is deleted

        with transaction.atomic():
            user = instance.user

            # delete user's support and help chats
            # messages in that chats will be deleted
            user.rooms.filter(type=Room.SUPPORT).delete()

            # delete user, brand will remain with user=NULL
            # all user's messages 'user' field in match and instant chats will be set to NULL
            user.delete()

            # need to call this before calling instance.save(),
            # cuz instance think that 'user' field was changed to NULL (and wasn't saved)
            # and it doesn't know user was deleted
            instance.refresh_from_db()

            Blog.objects.filter(brand=instance).delete()
            ProductPhoto.objects.filter(brand=instance).delete()
            GalleryPhoto.objects.filter(brand=instance).delete()
            BusinessGroup.objects.filter(brand=instance).delete()
            Subscription.objects.filter(brand=instance).update(is_active=False)  # deactivate active subscriptions
            # delete all blacklist entities where current brand is initiator or blocked
            BlackList.objects.filter(Q(initiator=instance) | Q(blocked=instance)).delete()

            # ---remove fields that are no value for analytics---
            for field in [
                'logo',
                'photo',
                'tg_nickname',
                'inst_url',
                'vk_url',
                'tg_url',
                'wb_url',
                'lamoda_url',
                'site_url',
                'uniqueness',
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

    @action(detail=False, methods=['get', 'patch', 'delete'], url_name='me')
    def me(self, request, *args, **kwargs):
        brand = request.user.brand
        if request.method == 'GET':
            serializer = self.get_serializer(brand)

            return Response(data=serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'PATCH':
            transformed_data = self.transform_request_data(request.data)

            instance = Brand.objects.select_related(
                'user',
                'category',
                'target_audience__age',
                'target_audience__gender'
            ).get(pk=request.user.brand.id)

            serializer = self.get_serializer(instance, data=transformed_data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(data=serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'DELETE':
            try:
                self.perform_destroy(brand)
            except DatabaseError:
                return Response({'detail': 'Unexpected database error. Please, try again!'})
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=['post'])
    def like(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def instant_coop(self, request):
        serializer = self.get_serializer(data={})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_name='liked_by')
    def liked_by(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_name='my_likes')
    def my_likes(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_name='my_matches')
    def my_matches(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_name='recommended_brands')
    def recommended_brands(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_name='statistics', pagination_class=None)
    def statistics(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return Response(data=serializer.data, status=status.HTTP_200_OK)


class CollaborationCreateView(generics.CreateAPIView):
    serializer_class = CollaborationSerializer
    permission_classes = [IsAuthenticated, IsBrand, HasActiveSub]
