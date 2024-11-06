import json
import os
import shutil

from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction, DatabaseError
from django.db.models import Q, Subquery, Prefetch, Value, Count
from django.http import QueryDict
from django.utils.functional import cached_property
from rest_framework import viewsets, status, generics, serializers, mixins
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.apps.analytics.models import BrandActivity
from core.apps.analytics.utils import log_brand_activity
from core.apps.brand.models import Brand, Category, Format, Goal, ProductPhoto, GalleryPhoto, Tag, BusinessGroup, Blog
from core.apps.brand.permissions import IsBusinessSub, IsBrand
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


class FasterDjangoPaginator(Paginator):
    # doesn't execute counting query
    @cached_property
    def count(self):
        return len(self.object_list)


class StandardResultsSetPagination(PageNumberPagination):
    django_paginator_class = FasterDjangoPaginator
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class BrandViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Brand.objects.all()
    serializer_class = BrandGetSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.action == 'liked_by':
            # get all brands which liked current one and haven't been liked in response yet
            liked_by_ids = self.request.user.brand.target.filter(is_match=False).values_list('initiator', flat=True)
            return Brand.objects.filter(pk__in=Subquery(liked_by_ids))

        elif self.action == 'my_likes':
            my_likes_ids = self.request.user.brand.initiator.filter(is_match=False).values_list('target', flat=True)

            # get all brands that were like by current brand.
            # Prefetch product_photos of format CARD to improve performance and set them to 'card_photos' attribute
            # prefetch instant rooms for brand user
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
            )

        elif self.action == 'my_matches':
            # get ids of brands that have match with current brand as initiator
            my_matches_ids_as_initiator = self.request.user.brand.initiator.filter(
                is_match=True
            ).values_list('target', flat=True)

            # get ids of brands that have match with current brand as target
            my_matches_ids_as_target = self.request.user.brand.target.filter(
                is_match=True
            ).values_list('initiator', flat=True)

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
            )

        elif self.action == 'recommended_brands':
            avg_bill = self.request.query_params.get('avg_bill')
            subs_count = self.request.query_params.get('subs_count')
            tags = self.request.query_params.getlist('tags')
            # TODO filter TA

            filter_kwargs = {}
            if avg_bill is not None:
                filter_kwargs['avg_bill'] = avg_bill

            if subs_count is not None:
                filter_kwargs['subs_count'] = subs_count

            if tags:
                filter_kwargs['tags__in'] = tags

            initial_brands = Brand.objects.filter(**filter_kwargs).distinct()

            current_brand = self.request.user.brand

            # get ids of current brand m2m and instantly evaluate it to avoid unnecessary subqueries
            current_brand_tags = list(current_brand.tags.values_list('id', flat=True))
            current_brand_formats = list(current_brand.formats.values_list('id', flat=True))
            current_brand_goals = list(current_brand.goals.values_list('id', flat=True))
            current_brand_categories_of_interest = list(
                current_brand.categories_of_interest.values_list('id', flat=True)
            )

            is_trial = False  # TODO change trial definition when trial is ready
            if is_trial:
                # priority1 only
                priority1 = initial_brands.filter(
                    tags__in=current_brand_tags,
                    avg_bill=current_brand.avg_bill,
                    subs_count=current_brand.subs_count
                ).distinct().exclude(
                    pk=current_brand.id
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(1),
                    tags_matches_num=Count('tags')
                )

                # priority1 ids
                priority1_ids = list(initial_brands.filter(
                    tags__in=current_brand_tags,
                    avg_bill=current_brand.avg_bill,
                    subs_count=current_brand.subs_count
                ).distinct().exclude(
                    pk=current_brand.id
                ).values_list('pk', flat=True))

                # priority2 only
                priority2 = initial_brands.filter(
                    tags__in=current_brand_tags,
                    avg_bill=current_brand.avg_bill
                ).distinct().exclude(
                    Q(pk=current_brand.id) | Q(pk__in=priority1_ids)
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(2),
                    tags_matches_num=Count('tags')
                )

                # priority2 ids
                priority2_ids = list(initial_brands.filter(
                    tags__in=current_brand_tags,
                    avg_bill=current_brand.avg_bill
                ).distinct().exclude(
                    Q(pk=current_brand.id) | Q(pk__in=priority1_ids)
                ).values_list('pk', flat=True))

                # priority3 only
                priority3 = initial_brands.filter(
                    tags__in=current_brand_tags
                ).distinct().exclude(
                    Q(pk=current_brand.id) | Q(pk__in=priority1_ids) | Q(pk__in=priority2_ids)
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(3),
                    tags_matches_num=Count('tags')
                )

                # priority3 ids
                priority3_ids = list(initial_brands.filter(
                    tags__in=current_brand_tags
                ).distinct().exclude(
                    Q(pk=current_brand.id) | Q(pk__in=priority1_ids) | Q(pk__in=priority2_ids)
                ).values_list('pk', flat=True))

                # priority4 only
                priority4 = initial_brands.exclude(
                    Q(pk=current_brand.id)
                    | Q(pk__in=priority1_ids)
                    | Q(pk__in=priority2_ids)
                    | Q(pk__in=priority3_ids)
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(4),
                    tags_matches_num=Value(0)
                )

                result = priority1.union(
                    priority2, priority3, priority4
                ).order_by(
                    'priority', '-tags_matches_num'
                )

                return result

            else:
                # priority1 only
                priority_1 = initial_brands.filter(
                    formats__in=current_brand_formats,
                    category__in=current_brand_categories_of_interest,
                    tags__in=current_brand_tags,
                    goals__in=current_brand_goals,
                    avg_bill=current_brand.avg_bill,
                    subs_count=current_brand.subs_count
                ).distinct().exclude(
                    pk=current_brand.id
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(1),
                    formats_matches_num=Count('formats'),
                    tags_matches_num=Count('tags'),
                    goals_matches_num=Count('goals'),
                )

                # priority1 ids
                # only ids, no annotation, no aggregation
                # used for excluding this priority objects from next-tier priority
                priority_1_ids = list(initial_brands.filter(
                    formats__in=current_brand_formats,
                    category__in=current_brand_categories_of_interest,
                    tags__in=current_brand_tags,
                    goals__in=current_brand_goals,
                    avg_bill=current_brand.avg_bill,
                    subs_count=current_brand.subs_count
                ).distinct().exclude(
                    pk=current_brand.id
                ).values_list('id', flat=True))

                # priority2 only
                priority_2 = initial_brands.filter(
                    formats__in=current_brand_formats,
                    category__in=current_brand_categories_of_interest,
                    tags__in=current_brand_tags,
                    goals__in=current_brand_goals,
                    avg_bill=current_brand.avg_bill
                ).distinct().exclude(
                    Q(pk=current_brand.id) | Q(pk__in=priority_1_ids)
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(2),
                    formats_matches_num=Count('formats'),
                    tags_matches_num=Count('tags'),
                    goals_matches_num=Count('goals'),
                )

                # priority2 ids
                priority_2_ids = list(initial_brands.filter(
                    formats__in=current_brand_formats,
                    category__in=current_brand_categories_of_interest,
                    tags__in=current_brand_tags,
                    goals__in=current_brand_goals,
                    avg_bill=current_brand.avg_bill
                ).distinct().exclude(
                    Q(pk=current_brand.id) | Q(pk__in=priority_1_ids)
                ).values_list('id', flat=True))

                # priority3 only
                priority_3 = initial_brands.filter(
                    formats__in=current_brand_formats,
                    category__in=current_brand_categories_of_interest,
                    tags__in=current_brand_tags,
                    goals__in=current_brand_goals,
                ).distinct().exclude(
                    Q(pk=current_brand.id) | Q(pk__in=priority_1_ids) | Q(pk__in=priority_2_ids)
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(3),
                    formats_matches_num=Count('formats'),
                    tags_matches_num=Count('tags'),
                    goals_matches_num=Count('goals'),
                )

                # priority3 ids
                priority_3_ids = list(initial_brands.filter(
                    formats__in=current_brand_formats,
                    category__in=current_brand_categories_of_interest,
                    tags__in=current_brand_tags,
                    goals__in=current_brand_goals,
                ).distinct().exclude(
                    Q(pk=current_brand.id) | Q(pk__in=priority_1_ids) | Q(pk__in=priority_2_ids)
                ).values_list('id', flat=True))

                # priority4 only
                priority_4 = initial_brands.filter(
                    formats__in=current_brand_formats,
                    category__in=current_brand_categories_of_interest,
                    tags__in=current_brand_tags,
                ).distinct().exclude(
                    Q(pk=current_brand.id)
                    | Q(pk__in=priority_1_ids)
                    | Q(pk__in=priority_2_ids)
                    | Q(pk__in=priority_3_ids)
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(4),
                    formats_matches_num=Count('formats'),
                    tags_matches_num=Count('tags'),
                    goals_matches_num=Value(0),
                )

                # priority4 ids
                priority_4_ids = list(initial_brands.filter(
                    formats__in=current_brand_formats,
                    category__in=current_brand_categories_of_interest,
                    tags__in=current_brand_tags,
                ).distinct().exclude(
                    Q(pk=current_brand.id)
                    | Q(pk__in=priority_1_ids)
                    | Q(pk__in=priority_2_ids)
                    | Q(pk__in=priority_3_ids)
                ).values_list('id', flat=True))

                # priority5 only
                priority_5 = initial_brands.filter(
                    formats__in=current_brand_formats,
                    category__in=current_brand_categories_of_interest,
                ).distinct().exclude(
                    Q(pk=current_brand.id)
                    | Q(pk__in=priority_1_ids)
                    | Q(pk__in=priority_2_ids)
                    | Q(pk__in=priority_3_ids)
                    | Q(pk__in=priority_4_ids)
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(5),
                    formats_matches_num=Count('formats'),
                    tags_matches_num=Value(0),
                    goals_matches_num=Value(0),
                )

                # priority5 ids
                priority_5_ids = list(initial_brands.filter(
                    formats__in=current_brand_formats,
                    category__in=current_brand_categories_of_interest,
                ).distinct().exclude(
                    Q(pk=current_brand.id)
                    | Q(pk__in=priority_1_ids)
                    | Q(pk__in=priority_2_ids)
                    | Q(pk__in=priority_3_ids)
                    | Q(pk__in=priority_4_ids)
                ).values_list('id', flat=True))

                # priority6 only
                priority_6 = initial_brands.filter(
                    formats__in=current_brand_formats,
                ).distinct().exclude(
                    Q(pk=current_brand.id)
                    | Q(pk__in=priority_1_ids)
                    | Q(pk__in=priority_2_ids)
                    | Q(pk__in=priority_3_ids)
                    | Q(pk__in=priority_4_ids)
                    | Q(pk__in=priority_5_ids)
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(6),
                    formats_matches_num=Count('formats'),
                    tags_matches_num=Value(0),
                    goals_matches_num=Value(0),
                )

                # priority6 ids
                priority_6_ids = list(initial_brands.filter(
                    formats__in=current_brand_formats,
                ).distinct().exclude(
                    Q(pk=current_brand.id)
                    | Q(pk__in=priority_1_ids)
                    | Q(pk__in=priority_2_ids)
                    | Q(pk__in=priority_3_ids)
                    | Q(pk__in=priority_4_ids)
                    | Q(pk__in=priority_5_ids)
                ).values_list('id', flat=True))

                # priority7 only
                priority_7 = initial_brands.exclude(
                    Q(pk=current_brand.id)
                    | Q(pk__in=priority_1_ids)
                    | Q(pk__in=priority_2_ids)
                    | Q(pk__in=priority_3_ids)
                    | Q(pk__in=priority_4_ids)
                    | Q(pk__in=priority_5_ids)
                    | Q(pk__in=priority_6_ids)
                ).prefetch_related(
                    Prefetch(
                        'product_photos',
                        queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                        to_attr='match_photos'
                    )
                ).annotate(
                    priority=Value(7),
                    formats_matches_num=Value(0),
                    tags_matches_num=Value(0),
                    goals_matches_num=Value(0),
                )

                # combine brands of all priorities and sort them
                result = priority_1.union(
                    priority_2, priority_3, priority_4, priority_5, priority_6, priority_7
                ).order_by('priority', '-formats_matches_num', '-tags_matches_num', '-goals_matches_num')

                return result

        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'create':
            return BrandCreateSerializer
        elif self.action == 'me':
            if self.request.method == 'GET':
                return BrandGetSerializer
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
        elif self.action == 'me':
            if self.request.method in ('GET', 'PATCH', 'DELETE'):
                permission_classes = [IsAuthenticated, IsBrand]
        elif self.action in ('like', 'liked_by', 'my_likes', 'my_matches', 'recommended_brands'):
            permission_classes = [IsAuthenticated, IsBrand]
        elif self.action == 'instant_coop':
            permission_classes = [IsAuthenticated, IsBrand, IsBusinessSub]
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
            user.rooms.filter(Q(type=Room.SUPPORT) | Q(type=Room.HELP)).delete()

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

    @action(detail=False, methods=['post'])
    def like(self, request):
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

    @action(detail=False, methods=['get'], url_name='liked_by')
    def liked_by(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_name='my_likes')
    def my_likes(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_name='my_matches')
    def my_matches(self, request):
        queryset = self.get_queryset()
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


class CollaborationCreateView(generics.CreateAPIView):
    serializer_class = CollaborationSerializer
    permission_classes = [IsAuthenticated, IsBrand]
