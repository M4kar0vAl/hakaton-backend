import os.path
import shutil
from functools import reduce

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction, DatabaseError
from django.db.models import Q, QuerySet
from rest_framework import serializers, exceptions

from core.apps.accounts.serializers import CreateUserSerializer
from core.apps.analytics.models import BrandActivity
from core.apps.analytics.utils import log_match_activity, log_brand_activity
from core.apps.brand.models import (
    Brand,
    Category,
    Format,
    Goal,
    Match,
    ProductPhoto,
    Age,
    Gender,
    GEO,
    TargetAudience,
    GalleryPhoto, Tag, BusinessGroup
)
from core.apps.chat.models import Room
from core.apps.payments.serializers import SubscriptionSerializer

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        exclude = []
        extra_kwargs = {'is_other': {'write_only': True, 'required': False}}


class FormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Format
        exclude = []
        extra_kwargs = {'is_other': {'write_only': True, 'required': False}}


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        exclude = []
        extra_kwargs = {'is_other': {'write_only': True, 'required': False}}


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        exclude = []
        extra_kwargs = {'is_other': {'write_only': True, 'required': False}}


class QuestionnaireChoicesSerializer(serializers.Serializer):
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    formats = FormatSerializer(many=True, read_only=True)
    goals = GoalSerializer(many=True, read_only=True)


# -----target audience serializers-----
class AgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Age
        exclude = ['id']


class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gender
        exclude = ['id']


class GEOSerializer(serializers.ModelSerializer):
    class Meta:
        model = GEO
        exclude = ['target_audience', 'id']


class TargetAudienceSerializer(serializers.ModelSerializer):
    age = AgeSerializer()
    gender = GenderSerializer()
    geos = GEOSerializer(many=True)

    class Meta:
        model = TargetAudience
        exclude = []


# -------------------------------------


class ProductPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPhoto
        exclude = ['brand']


class GalleryPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryPhoto
        exclude = ['brand']


class BusinessGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessGroup
        exclude = ['brand']


class BrandCreateSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    target_audience = TargetAudienceSerializer(required=False, allow_null=True)

    # photos write fields
    product_photos_match = serializers.ListField(child=serializers.ImageField(), write_only=True)
    product_photos_card = serializers.ListField(child=serializers.ImageField(), write_only=True)
    gallery_photos_list = serializers.ListField(child=serializers.ImageField(), required=False, write_only=True)

    # photos read fields
    product_photos = ProductPhotoSerializer(many=True, read_only=True)
    gallery_photos = GalleryPhotoSerializer(many=True, read_only=True)

    tags = TagSerializer(many=True)
    formats = FormatSerializer(many=True, required=False)
    goals = GoalSerializer(many=True, required=False)
    categories_of_interest = CategorySerializer(many=True, required=False)
    business_groups = BusinessGroupSerializer(many=True, required=False)

    class Meta:
        model = Brand
        # the only way to include non-model writable fields
        fields = [
            'id', 'tg_nickname', 'blog_url', 'name', 'position', 'category', 'inst_url', 'vk_url', 'tg_url', 'wb_url',
            'lamoda_url', 'site_url', 'subs_count', 'avg_bill', 'tags', 'uniqueness', 'logo', 'photo', 'description',
            'mission_statement', 'formats', 'goals', 'offline_space', 'problem_solving', 'target_audience',
            'categories_of_interest', 'business_groups', 'product_photos_match', 'product_photos_card',
            'gallery_photos_list', 'gallery_photos', 'product_photos'
        ]
        read_only_fields = ['user', 'sub_expire']

    def validate(self, attrs):
        category = attrs.get('category')
        if 'is_other' in category:
            if category['is_other']:
                # user selected "other" variant, so create category with given name
                category_obj = Category.objects.create(**category)
            else:
                try:
                    # user selected one of the given categories, so get instance from db
                    category_obj = Category.objects.get(**category)
                except Category.DoesNotExist:
                    raise exceptions.ValidationError(f"Category with name: {category['name']} does not exist!")
        else:
            try:
                # is_other wasn't passed, so get instance from db
                category_obj = Category.objects.get(**category)
            except Category.DoesNotExist:
                raise exceptions.ValidationError(f"Category with name: {category['name']} does not exist!")

        # if target audience wasn't passed, then data will not contain this key
        target_audience = attrs.get('target_audience')

        # -----target audience creation-----
        if target_audience is not None:
            try:
                with transaction.atomic():
                    # create age and gender
                    age_obj = Age.objects.create(**target_audience.pop('age'))
                    gender_obj = Gender.objects.create(**target_audience.pop('gender'))

                    # get geos request data
                    geos = target_audience.pop('geos')

                    # create target audience using age, gender and income
                    target_audience_obj = TargetAudience.objects.create(age=age_obj, gender=gender_obj,
                                                                        **target_audience)

                    # create geos objects in 1 query
                    GEO.objects.bulk_create([GEO(**geo, target_audience=target_audience_obj) for geo in geos])
            except Exception:
                raise exceptions.ValidationError(
                    "Failed to create target audience object. Check request data and try again"
                )
        else:
            target_audience_obj = None
        # ----------------------------------

        attrs['category'] = category_obj
        attrs['target_audience'] = target_audience_obj

        return attrs

    def create(self, validated_data):
        """
        Метод для создания бренда. Здесь обрабатываются поля-внешние ключи
        """
        # o2o
        user = self.context['request'].user

        # FK
        category = validated_data.pop('category')
        product_photos_match = validated_data.pop('product_photos_match')
        product_photos_card = validated_data.pop('product_photos_card')
        gallery_photos = validated_data.pop('gallery_photos_list')  # will be empty list if wasn't passed in form body
        business_groups = validated_data.pop('business_groups')

        # m2m
        tags = validated_data.pop('tags')

        try:
            formats = validated_data.pop('formats')
            goals = validated_data.pop('goals')
            cats_of_interest = validated_data.pop('categories_of_interest')
        except KeyError:
            formats = []
            goals = []
            cats_of_interest = []

        tags_query, tags_for_bulk_create = self.get_query_and_list_for_bulk_create(tags, Tag)

        if formats:
            formats_query, formats_for_bulk_create = self.get_query_and_list_for_bulk_create(formats, Format)

        if goals:
            goals_query, goals_for_bulk_create = self.get_query_and_list_for_bulk_create(goals, Goal)

        if cats_of_interest:
            cats_of_interest_query, cats_of_interest_for_bulk_create = self.get_query_and_list_for_bulk_create(
                cats_of_interest, Category
            )

        # Создаем объект бренда и связанных моделей в БД
        try:
            with transaction.atomic():
                brand = Brand.objects.create(
                    user=user, category=category, **validated_data
                )

                if business_groups:
                    BusinessGroup.objects.bulk_create([
                        BusinessGroup(**business_group, brand=brand) for business_group in business_groups
                    ])

                # -----handle m2m relations-----
                tag_list = self.get_list_for_m2m_relation(tags_query, tags_for_bulk_create, Tag)
                brand.tags.set(tag_list)

                if formats:
                    format_list = self.get_list_for_m2m_relation(formats_query, formats_for_bulk_create, Format)
                    brand.formats.set(format_list)

                if goals:
                    goal_list = self.get_list_for_m2m_relation(goals_query, goals_for_bulk_create, Goal)
                    brand.goals.set(goal_list)

                if cats_of_interest:
                    cats_of_interest_list = self.get_list_for_m2m_relation(
                        cats_of_interest_query, cats_of_interest_for_bulk_create, Category
                    )
                    brand.categories_of_interest.set(cats_of_interest_list)
                # ------------------------------

                # ----------photos----------
                # create lists of ProductPhoto objects
                product_photos_match_obj_list = [
                    ProductPhoto(image=photo, format=ProductPhoto.MATCH, brand=brand) for photo in product_photos_match
                ]
                product_photos_card_obj_list = [
                    ProductPhoto(image=photo, format=ProductPhoto.CARD, brand=brand) for photo in product_photos_card
                ]

                # create photos in db in 1 query per db table
                ProductPhoto.objects.bulk_create([*product_photos_match_obj_list, *product_photos_card_obj_list])

                if gallery_photos:
                    GalleryPhoto.objects.bulk_create(
                        [GalleryPhoto(image=photo, brand=brand) for photo in gallery_photos])
                # --------------------------

                log_brand_activity(brand=brand, action=BrandActivity.REGISTRATION)
        except Exception:
            try:
                # delete saved photos on server in case of exception
                shutil.rmtree(os.path.join(settings.MEDIA_ROOT, f"user_{self.context['request'].user.id}"))
            except FileNotFoundError:
                pass
            raise exceptions.ValidationError("Failed to perform action. Please, try again.")

        return brand

    def get_query_and_list_for_bulk_create(
            self, lst: list[dict], model: type[Tag] | type[Format] | type[Goal] | type[Category]
    ) -> (Q, list[Tag | Format | Goal | Category]):
        obj_list_for_query = [
            {**obj, 'is_other': False}
            for obj in lst if 'is_other' not in obj or not obj['is_other']
        ]

        obj_list_for_bulk_create = [
            model(**obj)
            for obj in lst if 'is_other' in obj and obj['is_other']
        ]

        query = reduce(lambda x, y: x | Q(**y), obj_list_for_query[1:], Q(**obj_list_for_query[0]))

        return query, obj_list_for_bulk_create

    def get_given_objects_from_db(
            self, query: Q, model: type[Tag] | type[Format] | type[Goal] | type[Category]
    ) -> QuerySet:
        """
        Get "given" objects from db
        """
        return model.objects.filter(query)

    def create_other_objects_in_db(
            self,
            other_list: list[Tag | Format | Goal | Category],
            model: type[Tag] | type[Format] | type[Goal] | type[Category]
    ) -> list[Tag | Format | Goal | Category]:
        """
        Create "other" objects in db in 1 query
        """
        return model.objects.bulk_create(other_list)

    def get_list_for_m2m_relation(
            self,
            query: Q,
            lst_for_bulk_create: list[Tag | Format | Goal | Category],
            model: type[Tag] | type[Format] | type[Goal] | type[Category],
    ) -> list[Tag | Format | Goal | Category]:
        """
        Get list to use in model.<related_name>.set()
        Gets "given" objects from db and creates "other" objects
        """
        objs = self.get_given_objects_from_db(query, model)
        other_objs = []
        if lst_for_bulk_create:
            other_objs = self.create_other_objects_in_db(lst_for_bulk_create, model)

        return list(objs) + other_objs


class BrandGetSerializer(serializers.ModelSerializer):
    user = CreateUserSerializer(read_only=True)  # TODO change to UserSerializer
    subscription = SubscriptionSerializer(read_only=True)
    category = CategorySerializer()
    goals = GoalSerializer(many=True)
    formats = FormatSerializer(many=True)

    class Meta:
        model = Brand
        exclude = []


class GetShortBrandSerializer(serializers.ModelSerializer):
    category = CategorySerializer()

    class Meta:
        model = Brand
        fields = [
            'id',
            'brand_name_pos',
            'fullname',
            'logo',
            'photo',
            'product_photo',
            'category'
        ]
        read_only_fields = [
            'id',
            'brand_name_pos',
            'fullname',
            'logo'
            'photo',
            'product_photo',
            'category'
        ]


class MatchSerializer(serializers.ModelSerializer):
    target = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), write_only=True)

    class Meta:
        model = Match
        exclude = ['id', 'initiator']
        read_only_fields = ['is_match', 'room']

    def validate(self, attrs):
        initiator = self.context['request'].user.brand
        target = attrs.get('target')

        if initiator == target:
            raise exceptions.ValidationError("You cannot 'like' yourself")

        try:
            # check if this brand have already performed that same 'like' action
            match = Match.objects.get(initiator=initiator, target=target)
            if match.is_match:
                raise exceptions.ValidationError(f"You already have 'match' with this brand! Room id: {match.room.pk}.")
            raise exceptions.ValidationError("You have already 'liked' this brand!")
        except Match.DoesNotExist:
            # at this point it means that there is no entry in db with that initiator and target,
            # BUT there may be a reverse entry, which is checked further
            pass

        try:
            # check if there is match
            match = Match.objects.get(initiator=target, target=initiator)
        except Match.DoesNotExist:
            match = None

        if match is not None and match.is_match:
            # if is_match = True already, then raise an exception
            raise exceptions.ValidationError(f"You already have 'match' with this brand! Room id: {match.room.pk}.")

        # at this point match is either None or is_match = False, passed to create method
        attrs['match'] = match
        attrs['initiator'] = initiator

        return attrs

    def create(self, validated_data):
        initiator = validated_data.get('initiator')
        target = validated_data.get('target')  # target contains Brand obj
        match = validated_data.get('match')

        try:
            with transaction.atomic():
                if match is not None:
                    # if not None, then is_match is False (checked in validate)
                    match.is_match = True
                    has_business = any([  # TODO change business sub definition
                        initiator.subscription and initiator.subscription.name == 'Бизнес',
                        target.subscription and target.subscription.name == 'Бизнес'
                    ])
                    room = Room.objects.create(has_business=has_business)
                    room.participants.add(initiator.user, target.user)
                    match.room = room
                    match.save()
                else:
                    match = Match.objects.create(initiator=initiator, target=target)

                log_match_activity(initiator=initiator, target=target, is_match=match.is_match)
        except DatabaseError:
            raise exceptions.ValidationError("Failed to perform action!")

        return match


class InstantCoopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        exclude = []
        read_only_fields = ['id', 'participants', 'has_business', 'type']

    def validate(self, attrs):
        initiator = self.context['request'].user.brand
        target_id = self.context['target_id']

        if initiator.pk == target_id:
            raise exceptions.ValidationError("You cannot cooperate with yourself!")

        try:
            target = Brand.objects.get(pk=target_id)
        except Brand.DoesNotExist:
            raise exceptions.NotFound(f"Brand with id: {target_id} not found!")

        try:
            # intersection of querysets
            # if initiator's instant rooms queryset and target's instant rooms queryset has common room,
            # then it means that they already have instant cooperation. No need to make another room
            common_room = (
                initiator.user.rooms.filter(type=Room.INSTANT).intersection(target.user.rooms.filter(type=Room.INSTANT))
            ).get()
            # if common room exist, then raise an exception.
            raise exceptions.ValidationError(f"You already have a chat with this brand! Room id: {common_room.pk}.")
        except Room.DoesNotExist:
            # if common room does not exist, then everything is fine. Continue and create one.
            pass

        attrs['initiator'] = initiator
        attrs['target'] = target

        return attrs

    def create(self, validated_data):
        initiator = validated_data.get('initiator')
        target = validated_data.get('target')

        room = Room.objects.create(has_business=True, type=Room.INSTANT)
        room.participants.add(initiator.user, target.user)

        return room


class InstantCoopRequestSerializer(serializers.Serializer):
    target = serializers.IntegerField(write_only=True)
