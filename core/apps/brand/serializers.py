import os
import shutil
from functools import reduce
from typing import Optional, Dict, List, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import TemporaryUploadedFile, InMemoryUploadedFile
from django.db import transaction, DatabaseError
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers, exceptions

from core.apps.accounts.serializers import UserSerializer
from core.apps.analytics.models import BrandActivity
from core.apps.analytics.utils import log_brand_activity
from core.apps.brand.mixins import BrandValidateMixin
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
    GalleryPhoto,
    Tag,
    BusinessGroup,
    Blog,
    Collaboration
)
from core.apps.chat.models import Room
from core.apps.cities.serializers import CitySerializer
from core.apps.payments.serializers import SubscriptionSerializer
from core.common.exceptions import ServerError

User = get_user_model()


class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        exclude = ['brand']


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

    def to_representation(self, instance):
        obj = super().to_representation(instance)

        obj['city'] = CitySerializer(instance.city).data

        return obj

    class Meta:
        model = GEO
        exclude = ['target_audience', 'id']


class TargetAudienceSerializer(serializers.ModelSerializer):
    age = AgeSerializer(allow_null=True)
    gender = GenderSerializer(allow_null=True)
    geos = GEOSerializer(many=True, allow_null=True)

    class Meta:
        model = TargetAudience
        exclude = ['id']
        extra_kwargs = {'income': {'allow_null': True}}


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


class BrandCreateSerializer(
    BrandValidateMixin,
    serializers.ModelSerializer
):
    user = UserSerializer(required=False, read_only=True)
    blogs = BlogSerializer(many=True, read_only=True)
    blogs_list = serializers.ListField(child=serializers.URLField(), write_only=True, required=False)
    category = CategorySerializer()
    tags = TagSerializer(many=True)

    # photos write fields
    product_photos_match = serializers.ListField(child=serializers.ImageField(), write_only=True)
    product_photos_card = serializers.ListField(child=serializers.ImageField(), write_only=True)

    # photos read fields
    product_photos = ProductPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Brand
        # the only way to include non-model writable fields
        fields = [
            'id', 'user', 'tg_nickname', 'city', 'blogs_list', 'blogs', 'name', 'position', 'category',
            'inst_url', 'vk_url', 'tg_url', 'wb_url', 'lamoda_url', 'site_url', 'subs_count', 'avg_bill', 'tags',
            'uniqueness', 'logo', 'photo', 'product_photos_match', 'product_photos_card', 'product_photos'
        ]
        extra_kwargs = {
            'city': {'required': True}
        }

    def to_representation(self, instance):
        obj = super().to_representation(instance)

        obj['city'] = CitySerializer(instance.city).data

        return obj

    def validate(self, attrs):
        if Brand.objects.filter(user=self.context['request'].user).exists():
            raise serializers.ValidationError('You already have brand!')

        return attrs

    def create(self, validated_data):
        """
        Метод для создания бренда. Здесь обрабатываются поля-внешние ключи
        """
        # ---------------o2o---------------
        user = self.context['request'].user

        # ---------------fk----------------
        # optional
        blogs = validated_data.pop('blogs_list', None)

        # required
        category = validated_data.pop('category')
        product_photos_match = validated_data.pop('product_photos_match')
        product_photos_card = validated_data.pop('product_photos_card')

        # ---------------m2m---------------
        tags = validated_data.pop('tags')

        # Создаем объект бренда и связанных моделей в БД
        try:
            with transaction.atomic():
                brand = Brand.objects.create(
                    user=user, category=category, **validated_data
                )

                # set created brand as an instance attribute to have access to it in other methods
                self.brand_instance = brand

                if blogs is not None:
                    self.create_blogs(blogs)

                # -----handle m2m relations-----
                self.create_and_set_tags(tags)

                # ----------photos----------
                self.create_product_photos(product_photos_card, product_photos_match)

                log_brand_activity(brand=brand, action=BrandActivity.REGISTRATION)
        except DatabaseError:
            try:
                # delete saved photos on server in case of exception
                shutil.rmtree(os.path.join(settings.MEDIA_ROOT, f"user_{self.context['request'].user.id}"))
            except FileNotFoundError:
                pass
            raise ServerError("Failed to perform action. Please, try again.")

        return brand

    def create_blogs(self, blogs: List[str]):
        Blog.objects.bulk_create([
            Blog(blog=blog, brand=self.brand_instance) for blog in blogs
        ])

    def create_and_set_tags(self, tags: List[Dict[str, Any]]):
        """
        Create tags that don't exist (with 'is_other' key).
        Set them to a brand
        """
        tag_list = self._get_list_for_m2m_relation(tags, Tag)
        self.brand_instance.tags.set(tag_list)

    def create_product_photos(
            self,
            card_photos: List[InMemoryUploadedFile | TemporaryUploadedFile],
            match_photos: List[InMemoryUploadedFile | TemporaryUploadedFile]
    ):
        product_photos_match_obj_list = [
            ProductPhoto(image=photo, format=ProductPhoto.MATCH, brand=self.brand_instance) for photo in match_photos
        ]
        product_photos_card_obj_list = [
            ProductPhoto(image=photo, format=ProductPhoto.CARD, brand=self.brand_instance) for photo in card_photos
        ]

        ProductPhoto.objects.bulk_create([*product_photos_match_obj_list, *product_photos_card_obj_list])

    def _get_list_for_m2m_relation(
            self,
            lst: list[dict],
            model: type[Tag] | type[Format] | type[Goal] | type[Category],
    ) -> list[Tag | Format | Goal | Category]:
        """
        Get list to use in model.<related_name>.set()
        Gets "given" objects from db and creates "other" objects
        """
        query, lst_for_bulk_create = self._get_query_and_list_for_bulk_create(lst, model)
        objs = model.objects.filter(query)
        other_objs = []

        if lst_for_bulk_create:
            other_objs = model.objects.bulk_create(lst_for_bulk_create)

        return list(objs) + other_objs

    def _get_query_and_list_for_bulk_create(
            self, lst: list[dict], model: type[Tag] | type[Format] | type[Goal] | type[Category]
    ) -> (Q, list[Tag | Format | Goal | Category]):
        """
        Get query to get existing objects from db and get a list of objects to create.
        """

        obj_list_for_query = [
            {**obj, 'is_other': False}
            for obj in lst if 'is_other' not in obj or not obj['is_other']
        ]

        obj_list_for_bulk_create = [
            model(**obj)
            for obj in lst if 'is_other' in obj and obj['is_other']
        ]

        # make query by combining Q objects for every obj in list using OR
        query = reduce(lambda x, y: x | Q(**y), obj_list_for_query[1:], Q(**obj_list_for_query[0]))

        return query, obj_list_for_bulk_create


class BrandCreateResponseSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False, read_only=True)
    city = CitySerializer(read_only=True)
    blogs = BlogSerializer(many=True, read_only=True)
    category = CategorySerializer()
    tags = TagSerializer(many=True)
    product_photos = ProductPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Brand
        fields = [
            'id', 'user', 'tg_nickname', 'city', 'blogs', 'name', 'position', 'category',
            'inst_url', 'vk_url', 'tg_url', 'wb_url', 'lamoda_url', 'site_url', 'subs_count', 'avg_bill', 'tags',
            'uniqueness', 'logo', 'photo', 'product_photos'
        ]


class BrandUpdateSerializer(
    BrandValidateMixin,
    serializers.ModelSerializer
):
    # write only
    new_blogs = serializers.ListField(child=serializers.CharField(), write_only=True)
    new_business_groups = serializers.ListField(child=serializers.CharField(), write_only=True)
    product_photos_match_add = serializers.ListField(child=serializers.ImageField(), write_only=True)
    product_photos_match_remove = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    product_photos_card_add = serializers.ListField(child=serializers.ImageField(), write_only=True)
    product_photos_card_remove = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    gallery_add = serializers.ListField(child=serializers.ImageField(), write_only=True)
    gallery_remove = serializers.ListField(child=serializers.IntegerField(), write_only=True)

    # read only
    blogs = BlogSerializer(many=True, read_only=True)
    business_groups = BusinessGroupSerializer(many=True, read_only=True)
    gallery_photos = GalleryPhotoSerializer(many=True, read_only=True)
    product_photos = ProductPhotoSerializer(many=True, read_only=True)

    category = CategorySerializer()
    tags = TagSerializer(many=True)
    formats = FormatSerializer(many=True)
    goals = GoalSerializer(many=True)
    target_audience = TargetAudienceSerializer()
    categories_of_interest = CategorySerializer(many=True)

    class Meta:
        model = Brand
        fields = [
            'tg_nickname', 'city', 'new_blogs', 'blogs', 'name', 'position', 'category', 'inst_url', 'vk_url', 'tg_url',
            'wb_url', 'lamoda_url', 'site_url', 'subs_count', 'avg_bill', 'tags', 'uniqueness', 'logo', 'photo',
            'mission_statement', 'formats', 'goals', 'offline_space', 'problem_solving',
            'target_audience', 'categories_of_interest', 'business_groups', 'new_business_groups',
            'product_photos_match_add', 'product_photos_match_remove', 'product_photos_card_add',
            'product_photos_card_remove', 'gallery_add', 'gallery_remove',
            'gallery_photos', 'product_photos',
        ]

    def to_representation(self, instance):
        obj = super().to_representation(instance)

        obj['city'] = CitySerializer(instance.city).data

        return obj

    def validate(self, attrs):
        match_add = attrs.get('product_photos_match_add', [])
        match_remove = attrs.get('product_photos_match_remove', [])
        card_add = attrs.get('product_photos_card_add', [])
        card_remove = attrs.get('product_photos_card_remove', [])

        current_match_num = self.instance.product_photos.filter(format=ProductPhoto.MATCH).count()
        current_card_num = self.instance.product_photos.filter(format=ProductPhoto.CARD).count()

        if current_match_num + len(match_add) - len(match_remove) <= 0:
            raise serializers.ValidationError('The overall number of match product photos cannot be <= 0')

        if current_card_num + len(card_add) - len(card_remove) <= 0:
            raise serializers.ValidationError('The overall number of brand card product photos cannot be <= 0')

        return attrs

    def update(self, instance, validated_data):
        # ----------o2o----------
        target_audience = validated_data.pop('target_audience', None)

        # ----------fk-----------
        category = validated_data.pop('category', None)
        city = validated_data.pop('city', None)

        # ----------m2m----------
        new_tags = validated_data.pop('tags', None)
        new_formats = validated_data.pop('formats', None)
        new_goals = validated_data.pop('goals', None)
        new_cats = validated_data.pop('categories_of_interest', None)

        # ----------o2m----------
        new_blogs = validated_data.pop('new_blogs', None)
        new_business_groups = validated_data.pop('new_business_groups', None)

        # ----------o2m photos----------
        gallery_add = validated_data.pop('gallery_add', None)
        gallery_remove = validated_data.pop('gallery_remove', None)
        product_photos_match_add = validated_data.pop('product_photos_match_add', None)
        product_photos_match_remove = validated_data.pop('product_photos_match_remove', None)
        product_photos_card_add = validated_data.pop('product_photos_card_add', None)
        product_photos_card_remove = validated_data.pop('product_photos_card_remove', None)

        try:
            with transaction.atomic():
                # -----update non-complex fields-----
                for field in [
                    'tg_nickname',
                    'name',
                    'position',
                    'inst_url',
                    'vk_url',
                    'tg_url',
                    'wb_url',
                    'lamoda_url',
                    'site_url',
                    'subs_count',
                    'avg_bill',
                    'uniqueness',
                    'mission_statement',
                    'offline_space',
                    'problem_solving',
                    'logo',
                    'photo',
                ]:
                    if field in validated_data:
                        setattr(instance, field, validated_data[field])
                # -----------------------------------

                if city is not None:
                    instance.city = city

                if category is not None:
                    self.update_category(category)

                if new_blogs is not None:
                    self.update_blogs(new_blogs)

                if new_business_groups is not None:
                    self.update_business_groups(new_business_groups)

                if new_tags is not None:
                    self.update_tags(new_tags)

                if new_formats is not None:
                    self.update_formats(new_formats)

                if new_goals is not None:
                    self.update_goals(new_goals)

                if new_cats is not None:
                    self.update_categories_of_interset(new_cats)

                if target_audience is not None:
                    self.create_or_update_target_audience(target_audience)

                if product_photos_card_add or product_photos_card_remove:
                    self.update_product_photos(
                        product_photos_card_remove, product_photos_card_add, ProductPhoto.CARD
                    )

                if product_photos_match_add or product_photos_match_remove:
                    self.update_product_photos(
                        product_photos_match_remove, product_photos_match_add, ProductPhoto.MATCH
                    )

                if gallery_add or gallery_remove:
                    self.update_gallery_photos(gallery_remove, gallery_add)

                instance.save()
        except DatabaseError:
            raise ServerError('Failed to perform action! Please, try again.')

        return instance

    def validate_gallery_remove(self, ids):
        self._validate_o2m_photos_remove(ids, GalleryPhoto)
        return ids

    def validate_product_photos_card_remove(self, ids):
        self._validate_o2m_photos_remove(ids, ProductPhoto, ProductPhoto.CARD)
        return ids

    def validate_product_photos_match_remove(self, ids):
        self._validate_o2m_photos_remove(ids, ProductPhoto, ProductPhoto.MATCH)
        return ids

    def _validate_o2m_photos_remove(self, ids, model: type[GalleryPhoto | ProductPhoto], format_=None):
        format_kwarg = {'format': format_} if format_ is not None else {}
        to_remove_num = model.objects.filter(pk__in=ids, brand=self.instance, **format_kwarg).count()
        requested_to_remove = len(ids)

        if to_remove_num != requested_to_remove:
            raise serializers.ValidationError(
                "Number of files and objects selected for removal do not match! "
                f"Requested: {requested_to_remove}, found: {to_remove_num}"
            )

    def update_category(self, category):
        current_category = self.instance.category  # remember current category

        # update category
        self.instance.category = category
        self.instance.save()

        # delete old category if it is 'other'
        if current_category.is_other:
            current_category.delete()

    def update_blogs(self, new_blogs):
        self._update_o2m(new_blogs, 'blog', Blog, 'blogs')

    def update_business_groups(self, new_business_groups):
        self._update_o2m(new_business_groups, 'name', BusinessGroup, 'business_groups')

    def _update_o2m(
            self,
            new_objs: list[str],
            lookup_field: str,
            model: type[Blog] | type[BusinessGroup],
            related_name: str
    ) -> None:
        if not new_objs:
            getattr(self.instance, related_name).all().delete()
            return

        # delete unnecessary objs
        getattr(self.instance, related_name).filter(~Q(**{f'{lookup_field}__in': new_objs})).delete()
        # create added objs
        current_objs_names = getattr(self.instance, related_name).values_list(lookup_field, flat=True)
        to_add = [
            model(**{lookup_field: obj_value}, brand=self.instance)
            for obj_value in new_objs if obj_value not in current_objs_names
        ]
        if to_add:
            model.objects.bulk_create(to_add)

    def update_tags(self, new_tags):
        self._update_m2m(new_tags, Tag, 'tags')

    def update_formats(self, new_formats):
        self._update_m2m(new_formats, Format, 'formats')

    def update_goals(self, new_goals):
        self._update_m2m(new_goals, Goal, 'goals')

    def update_categories_of_interset(self, new_cats):
        self._update_m2m(new_cats, Category, 'categories_of_interest')

    def _update_m2m(
            self,
            obj_list: list[dict],
            model: type[Tag] | type[Format] | type[Goal] | type[Category],
            related_name: str
    ) -> None:
        # TODO try to optimize somehow
        new_common_objs_names, new_other_objs_names = self._split_common_other(obj_list)

        if not new_common_objs_names and not new_other_objs_names:
            # if empty list passed in request, then delete current brand 'other' obj and unset all associated objects
            getattr(self.instance, related_name).filter(is_other=True).delete()
            getattr(self.instance, related_name).clear()
            return

        # other obj may be only one, checked in validate
        other = []
        if new_other_objs_names:
            # if there is 'other' in request
            try:
                # check if 'other' in new objs list already exists and if so assign it to 'other' variable
                existing_other = getattr(self.instance, related_name).get(is_other=True, name=new_other_objs_names[0])
                other = [existing_other]
            except model.DoesNotExist:
                # if 'other' from request does not exist, then delete current and create a new one
                # delete current 'other' obj
                getattr(self.instance, related_name).filter(is_other=True).delete()

                # create new 'other' obj
                other = [model.objects.create(name=new_other_objs_names[0], is_other=True)]
        else:
            # if 'other' wasn't passed in request, then delete current 'other'
            getattr(self.instance, related_name).filter(is_other=True).delete()

        common = model.objects.filter(name__in=new_common_objs_names, is_other=False)  # new common objs

        # will remove objs that are not in new list, will add only objs that are not already set
        getattr(self.instance, related_name).set(list(common) + other)

    def _split_common_other(self, obj_list: list[dict]) -> tuple[list[str], list[str]]:
        new_common_objs_names = []
        new_other_objs_names = []

        for obj in obj_list:
            if 'is_other' in obj:
                if obj['is_other']:
                    new_other_objs_names.append(obj['name'])
                else:
                    new_common_objs_names.append(obj['name'])
            else:
                new_common_objs_names.append(obj['name'])

        return new_common_objs_names, new_other_objs_names

    def update_product_photos(
            self,
            to_remove: List[int],
            to_add: List[InMemoryUploadedFile | TemporaryUploadedFile],
            format_: str
    ):
        self._update_o2m_photos(ProductPhoto, 'product_photos', to_remove, to_add, format_)

    def update_gallery_photos(
            self,
            to_remove: List[int],
            to_add: List[InMemoryUploadedFile | TemporaryUploadedFile]
    ):
        self._update_o2m_photos(GalleryPhoto, 'gallery_photos', to_remove, to_add)

    def _update_o2m_photos(
            self,
            model,
            related_name: str,
            to_remove: List[int] = None,
            to_add: List[InMemoryUploadedFile | TemporaryUploadedFile] = None,
            format_: str = None
    ):
        format_kwarg = {'format': format_} if format_ is not None else {}

        if to_remove:
            getattr(self.instance, related_name).filter(pk__in=to_remove, **format_kwarg).delete()

        if to_add:
            model.objects.bulk_create([
                model(brand=self.instance, image=image, **format_kwarg)
                for image in to_add
            ])

    def create_or_update_target_audience(self, new_target_audience: Dict[str, Any]) -> None:
        current_target_audience = self.instance.target_audience  # get current audience

        if current_target_audience is None:
            # if no target audience yet, then create it
            current_target_audience = TargetAudience.objects.create()
            self.instance.target_audience = current_target_audience
            self.instance.save()

        age: Optional[Dict[str, int]] = new_target_audience.get('age')

        # update target audience fields or populate them
        if age is not None:
            if not age:
                # if empty dict
                if current_target_audience.age is not None:
                    # if current age is not NULL, then remove current age, age attribute will be set to NULL
                    current_target_audience.age.delete()
                    # need to call it before .save() when deleting related object
                    current_target_audience.refresh_from_db()
            else:
                if current_target_audience.age is None:
                    # create age if current age is None
                    age_obj = Age.objects.create(**age)
                    current_target_audience.age = age_obj
                else:
                    # otherwise update it
                    current_target_audience.age.men = age.get('men', current_target_audience.age.men)
                    current_target_audience.age.women = age.get('women', current_target_audience.age.women)
                    current_target_audience.age.save()

        gender: Optional[Dict[str, int]] = new_target_audience.get('gender')

        if gender is not None:
            if not gender:
                if current_target_audience.gender is not None:
                    current_target_audience.gender.delete()
                    current_target_audience.refresh_from_db()
            else:
                if current_target_audience.gender is None:
                    gender_obj = Gender.objects.create(**gender)
                    current_target_audience.gender = gender_obj
                else:
                    current_target_audience.gender.men = gender.get(
                        'men', current_target_audience.gender.men
                    )
                    current_target_audience.gender.women = gender.get(
                        'women', current_target_audience.gender.women
                    )
                    current_target_audience.gender.save()

        income: Optional[int] = new_target_audience.get('income', -1)

        if income != -1:
            # if income is in request data
            if income is None:
                # if None, then set value to NULL in db
                current_target_audience.income = None
            else:
                # otherwise update it
                current_target_audience.income = income

        geos: Optional[List[Dict[str, Any]]] = new_target_audience.get('geos')

        if geos is not None:
            if not geos:
                current_target_audience.geos.all().delete()
            else:
                new_geos_cities = [geo['city'] for geo in geos]  # cities objs

                # delete geos with cities that are not in new cities list
                current_target_audience.geos.filter(~Q(city__in=new_geos_cities)).delete()

                # get remaining geos
                current_geos_cities = current_target_audience.geos.values_list('city', flat=True)

                # split geos on to_update and to_create
                to_update = []
                to_create = []
                for geo in geos:
                    if geo['city'].id in current_geos_cities:
                        to_update.append(geo)
                    else:
                        to_create.append(GEO(
                            city=geo['city'],  # geo['city'] is City obj
                            people_percentage=geo['people_percentage'],
                            target_audience=current_target_audience)
                        )

                # update existing
                if to_update:
                    for geo in to_update:
                        current_target_audience.geos \
                            .filter(city=geo['city']) \
                            .update(people_percentage=geo['people_percentage'])

                # create new ones
                if to_create:
                    GEO.objects.bulk_create(to_create)

        current_target_audience.save()


class BrandGetSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    blogs = BlogSerializer(many=True, read_only=True)
    city = CitySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    goals = GoalSerializer(many=True, read_only=True)
    formats = FormatSerializer(many=True, read_only=True)
    categories_of_interest = CategorySerializer(many=True, read_only=True)
    business_groups = BusinessGroupSerializer(many=True, read_only=True)
    gallery_photos = GalleryPhotoSerializer(many=True, read_only=True)
    product_photos = ProductPhotoSerializer(many=True, read_only=True)
    target_audience = TargetAudienceSerializer(read_only=True)

    class Meta:
        model = Brand
        exclude = []


class BrandMeSerializer(BrandGetSerializer):
    subscription = serializers.SerializerMethodField(read_only=True)

    @extend_schema_field(SubscriptionSerializer())
    def get_subscription(self, brand):
        sub = brand.get_active_subscription(True)

        return sub and SubscriptionSerializer(sub).data  # if sub is None return None, otherwise return sub data


class GetShortBrandSerializer(serializers.ModelSerializer):
    category = CategorySerializer()

    class Meta:
        model = Brand
        fields = [
            'id',
            'name',
            'logo',
            'photo',
            'category'
        ]
        read_only_fields = [
            'id',
            'name',
            'logo'
            'photo',
            'category'
        ]


class MatchSerializer(serializers.ModelSerializer):
    target = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), write_only=True)

    class Meta:
        model = Match
        exclude = ['initiator']
        read_only_fields = ['id', 'is_match', 'room']

    def validate(self, attrs):
        initiator = self.context['request'].user.brand
        target = attrs.get('target')

        if initiator == target:
            raise serializers.ValidationError("You cannot 'like' yourself")

        try:
            # check if this brand have already performed that same 'like' action
            match = Match.objects.get(initiator=initiator, target=target)
            if match.is_match:
                raise serializers.ValidationError(
                    f"You already have 'match' with this brand! Room id: {match.room.pk}.")
            raise serializers.ValidationError("You have already 'liked' this brand!")
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
            raise serializers.ValidationError(f"You already have 'match' with this brand! Room id: {match.room.pk}.")

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
                    match.match_at = timezone.now()

                    if match.room is not None:
                        # if match already have room (instant), then change its type to match
                        match.room.type = Room.MATCH
                        match.room.save()
                    else:
                        room = Room.objects.create(type=Room.MATCH)
                        room.participants.add(initiator.user, target.user)
                        match.room = room
                    match.save()
                else:
                    match = Match.objects.create(initiator=initiator, target=target)
        except DatabaseError:
            raise ServerError("Failed to perform action!")

        return match


class InstantCoopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        exclude = []
        read_only_fields = ['id', 'participants', 'type']

    def validate(self, attrs):
        initiator = self.context['request'].user.brand
        target_id = self.context['target_id']

        if initiator.pk == target_id:
            raise serializers.ValidationError("You cannot cooperate with yourself!")

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
            raise serializers.ValidationError(f"You already have a chat with this brand! Room id: {common_room.pk}.")
        except Room.DoesNotExist:
            # if common room does not exist, then everything is fine. Continue and create one.
            pass

        attrs['initiator'] = initiator
        attrs['target'] = target

        return attrs

    def create(self, validated_data):
        initiator = validated_data.get('initiator')
        target = validated_data.get('target')

        try:
            with transaction.atomic():
                room = Room.objects.create(type=Room.INSTANT)
                room.participants.add(initiator.user, target.user)

                # assign instant room to this like.
                # Like MUST exist because otherwise permission will be denied (see brand.permissions.CanInstantCoop)
                Match.objects.filter(
                    initiator=initiator,
                    target=target,
                    is_match=False
                ).update(room=room)
        except DatabaseError:
            raise ServerError('Failed to perform action. Please, try again!')

        return room


class InstantCoopRequestSerializer(serializers.Serializer):
    target = serializers.IntegerField(write_only=True)


class CollaborationSerializer(serializers.ModelSerializer):
    match = serializers.PrimaryKeyRelatedField(queryset=Match.objects.filter(is_match=True))

    class Meta:
        model = Collaboration
        exclude = []
        read_only_fields = ['reporter', 'collab_with', 'created_at']

    def validate(self, attrs):
        reporter = self.context['request'].user.brand
        match = attrs.get('match')  # match obj

        match_initiator_id = match.initiator_id
        match_target_id = match.target_id

        collab_with_id = None

        if reporter.id == match_initiator_id:
            # if the brand is the initiator of the match, then collab_with is the target
            collab_with_id = match_target_id
        elif reporter.id == match_target_id:
            # if the brand is the target of the match, then collab_with is the initiator
            collab_with_id = match_initiator_id

        if collab_with_id is None:
            # if brand is not the initiator and not the target of the match, then this is not the brand's match
            raise serializers.ValidationError('You cannot report a collaboration unless you are a member of the match.')

        collab_with = Brand.objects.get(id=collab_with_id)

        if reporter.id == collab_with_id:
            raise serializers.ValidationError('You cannot report a collaboration with yourself!')

        if Collaboration.objects.filter(reporter=reporter, collab_with=collab_with).exists():
            raise serializers.ValidationError("You have already reported collaboration with that brand!")

        attrs['reporter'] = reporter
        attrs['collab_with'] = collab_with

        return attrs

    def create(self, validated_data):
        reporter = validated_data.pop('reporter')
        collab_with = validated_data.pop('collab_with')

        try:
            with transaction.atomic():
                collab = Collaboration.objects.create(reporter=reporter, collab_with=collab_with, **validated_data)
                # TODO add points to reported brand
        except DatabaseError:
            raise ServerError("Failed to perform action!")

        return collab


class LikedBySerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'logo']


class MyLikesSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    product_photos_card = serializers.SerializerMethodField()
    instant_room = serializers.SerializerMethodField()
    user_fullname = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = [
            'id', 'instant_room', 'product_photos_card', 'user_fullname',
            'name', 'photo', 'uniqueness', 'city', 'subs_count'
        ]

    @extend_schema_field(ProductPhotoSerializer(many=True))
    def get_product_photos_card(self, brand):
        # card_photos are prefetched in BrandViewSet.get_queryset method
        return ProductPhotoSerializer(brand.card_photos, many=True).data

    @extend_schema_field(serializers.CharField)
    def get_user_fullname(self, brand):
        return brand.user.fullname

    @extend_schema_field(serializers.IntegerField)
    def get_instant_room(self, brand):
        """
        Get instant room id for a pair of current user and liked brand user for each brand in queryset

        Returns:
            id of a common instant room if it exists or None if it doesn't

        To avoid N + 1 problems:
         - rooms are being prefetched for each brand in BrandViewSet.get_queryset method
         - current user rooms ids are evaluated when calling BrandViewSet.get_serializer_context method
         - intersection of sets is made in python
        """
        current_user_instant_rooms_ids = self.context['current_user_instant_rooms_ids']

        # get a set of instant rooms ids
        brand_user_instant_rooms_ids = set(room.id for room in brand.user.instant_rooms)

        # intersection of sets, get common ids
        # result expected to be a set containing one integer because every pair of users can only have 1 instant room
        # OR empty set if there is no instant cooperation between these brands
        common_room_id_set = current_user_instant_rooms_ids & brand_user_instant_rooms_ids

        if not common_room_id_set:
            return None

        # extract id from set
        [common_room_id] = common_room_id_set

        return common_room_id


class MyMatchesSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    product_photos_card = serializers.SerializerMethodField()
    match_room = serializers.SerializerMethodField()
    user_fullname = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = [
            'id', 'match_room', 'product_photos_card', 'user_fullname',
            'name', 'photo', 'uniqueness', 'city', 'subs_count'
        ]

    @extend_schema_field(ProductPhotoSerializer(many=True))
    def get_product_photos_card(self, brand):
        return ProductPhotoSerializer(brand.card_photos, many=True).data

    @extend_schema_field(serializers.CharField)
    def get_user_fullname(self, brand):
        return brand.user.fullname

    @extend_schema_field(serializers.IntegerField)
    def get_match_room(self, brand):
        current_user_match_rooms_ids = self.context['current_user_match_rooms_ids']
        brand_user_match_rooms_ids = set(room.id for room in brand.user.match_rooms)  # get a set of match rooms ids

        # get common room set for current pair of users
        # result expected to be a set containing one integer because every pair of users can only have 1 match room
        common_room_id_set = current_user_match_rooms_ids & brand_user_match_rooms_ids

        [common_room] = common_room_id_set

        return common_room


class RecommendedBrandsSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    category = CategorySerializer()
    match_photos = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = [
            'id', 'name', 'city', 'subs_count', 'logo', 'category', 'uniqueness', 'match_photos'
        ]

    @extend_schema_field(ProductPhotoSerializer(many=True))
    def get_match_photos(self, brand):
        return ProductPhotoSerializer(brand.match_photos, many=True).data


class StatisticsSerializer(serializers.Serializer):
    period = serializers.CharField(read_only=True)
    likes = serializers.IntegerField(read_only=True)
    matches = serializers.IntegerField(read_only=True)
    collabs = serializers.IntegerField(read_only=True)
