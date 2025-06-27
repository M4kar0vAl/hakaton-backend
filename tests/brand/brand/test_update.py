import glob
import json
import os

import factory
from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Q
from django.test import override_settings, tag
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import (
    BrandFactory,
    BlogFactory,
    CategoryFactory,
    ProductPhotoFactory,
    TagFactory,
    FormatFactory,
    GoalFactory,
    BusinessGroupFactory,
    GalleryPhotoFactory,
    TargetAudienceFactory,
    AgeFactory,
    GenderFactory,
    GeoFactory
)
from core.apps.brand.models import Brand, Tag, ProductPhoto, Age, Gender, Category, Format, Goal
from core.apps.cities.factories import CityFactory
from tests.utils import refresh_api_settings


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
    REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        'TEST_REQUEST_DEFAULT_FORMAT': 'multipart',
    },
)
@tag('slow')
class BrandUpdateTestCase(APITransactionTestCase):  # django-cleanup requires TransactionTestCase to be used
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        refresh_api_settings()

    def setUp(self):
        self.user = UserFactory()
        self.auth_client = APIClient()
        self.auth_client.force_authenticate(self.user)

        self.brand = BrandFactory(
            user=self.user,
            tags=TagFactory.create_batch(3),
            formats=FormatFactory.create_batch(3),
            goals=GoalFactory.create_batch(3),
            categories_of_interest=CategoryFactory.create_batch(3)
        )

        self.initial_match_photos_num = self.brand.product_photos.filter(format=ProductPhoto.MATCH).count()
        self.initial_card_photos_num = self.brand.product_photos.filter(format=ProductPhoto.CARD).count()
        self.initial_gallery_photos_num = self.brand.gallery_photos.count()

        self.new_image_width = 150
        self.update_data = factory.build(
            dict,
            FACTORY_CLASS=BrandFactory,
            user=None,
            blogs=None,
            product_photos=None,
            category=None,
            city=None,
            business_groups=None,
            gallery_photos=None,
            target_audience=None,
            logo__width=self.new_image_width,
            photo__width=self.new_image_width,
        )

        del self.update_data['user']
        del self.update_data['blogs']
        del self.update_data['product_photos']
        del self.update_data['business_groups']
        del self.update_data['gallery_photos']

        self.city1, self.city2 = CityFactory.create_batch(2)
        self.category = CategoryFactory()

        blogs_data = factory.build_batch(dict, size=2, FACTORY_CLASS=BlogFactory)
        self.new_blogs = list(map(lambda x: x['blog'], blogs_data))

        business_groups_data = factory.build_batch(dict, size=2, FACTORY_CLASS=BusinessGroupFactory)
        self.new_business_groups = list(map(lambda x: x['name'], business_groups_data))

        product_photos = factory.build_batch(
            dict, size=4, FACTORY_CLASS=ProductPhotoFactory, image__width=self.new_image_width
        )
        self.product_photos_match_add = list(
            map(lambda x: x['image'], filter(lambda x: x['format'] == ProductPhoto.MATCH, product_photos))
        )
        self.product_photos_match_remove = list(
            self.brand.product_photos.filter(format=ProductPhoto.MATCH).values_list('pk', flat=True)
        )
        self.product_photos_card_add = list(
            map(lambda x: x['image'], filter(lambda x: x['format'] == ProductPhoto.CARD, product_photos))
        )
        self.product_photos_card_remove = list(
            self.brand.product_photos.filter(format=ProductPhoto.CARD).values_list('pk', flat=True)
        )

        gallery_photos = factory.build_batch(
            dict, 2, FACTORY_CLASS=GalleryPhotoFactory, image__width=self.new_image_width
        )
        self.gallery_add = list(map(lambda x: x['image'], gallery_photos))
        self.gallery_remove = list(self.brand.gallery_photos.values_list('pk', flat=True))

        self.tags = TagFactory.create_batch(2)
        self.tags_as_dicts = list(map(lambda tag_: {'name': tag_.name}, self.tags))
        self.other_tag = factory.build(dict, FACTORY_CLASS=TagFactory, is_other=True)

        self.formats = FormatFactory.create_batch(2)
        self.formats_as_dicts = list(map(lambda format_: {'name': format_.name}, self.formats))
        self.other_format = factory.build(dict, FACTORY_CLASS=FormatFactory, is_other=True)

        self.goals = GoalFactory.create_batch(2)
        self.goals_as_dicts = list(map(lambda goal: {'name': goal.name}, self.goals))
        self.other_goal = factory.build(dict, FACTORY_CLASS=GoalFactory, is_other=True)

        self.categories_of_interest = CategoryFactory.create_batch(2)
        self.categories_of_interest_as_dicts = list(
            map(lambda category: {'name': category.name}, self.categories_of_interest))
        self.other_category_of_interest = factory.build(dict, FACTORY_CLASS=CategoryFactory, is_other=True)

        self.age = factory.build(dict, FACTORY_CLASS=AgeFactory)
        self.gender = factory.build(dict, FACTORY_CLASS=GenderFactory)
        self.geos = factory.build_batch(
            dict, 2, FACTORY_CLASS=GeoFactory, city=factory.Iterator([self.city1.pk, self.city2.pk])
        )

        self.geos_query = Q()
        for geo in self.geos:
            del geo['target_audience']
            self.geos_query |= Q(**geo)

        self.target_audience = factory.build(
            dict, FACTORY_CLASS=TargetAudienceFactory, age=self.age, gender=self.gender, geos=self.geos
        )

        self.update_data['city'] = self.city1.pk
        self.update_data['category'] = json.dumps({'name': self.category.name})
        self.update_data['new_blogs'] = json.dumps(self.new_blogs)
        self.update_data['new_business_groups'] = json.dumps(self.new_business_groups)
        self.update_data['product_photos_match_add'] = self.product_photos_match_add
        self.update_data['product_photos_match_remove'] = json.dumps(self.product_photos_match_remove)
        self.update_data['product_photos_card_add'] = self.product_photos_card_add
        self.update_data['product_photos_card_remove'] = json.dumps(self.product_photos_card_remove)
        self.update_data['gallery_add'] = self.gallery_add
        self.update_data['gallery_remove'] = json.dumps(self.gallery_remove)
        self.update_data['tags'] = json.dumps([*self.tags_as_dicts, self.other_tag])
        self.update_data['formats'] = json.dumps([*self.formats_as_dicts, self.other_format])
        self.update_data['goals'] = json.dumps([*self.goals_as_dicts, self.other_goal])
        self.update_data['categories_of_interest'] = json.dumps(
            [*self.categories_of_interest_as_dicts, self.other_category_of_interest]
        )
        self.update_data['target_audience'] = json.dumps(self.target_audience)

        self.new_image_size = self.update_data['logo'].size

        self.url = reverse('brand-me')

    def test_brand_put_not_allowed(self):
        response = self.auth_client.put(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_brand_update_unauthenticated_not_allowed(self):
        response = self.client.patch(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_brand_update_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)
        response = auth_client_wo_brand.patch(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_brand_partial_update_whole_data(self):
        response = self.auth_client.patch(self.url, self.update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_brand = Brand.objects.select_related(
            'category',
            'target_audience__age',
            'target_audience__gender'
        ).get(pk=self.brand.id)

        # check simple fields
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
        ]:
            self.assertEqual(getattr(updated_brand, field), self.update_data[field])

        # check blogs
        self.assertEqual(updated_brand.blogs.count(), len(self.new_blogs))
        self.assertEqual(updated_brand.blogs.filter(blog__in=self.new_blogs).count(), len(self.new_blogs))

        # check city
        self.assertEqual(updated_brand.city.id, self.update_data['city'])

        # check category
        self.assertEqual(updated_brand.category.name, self.category.name)

        # check tags
        self.assertEqual(updated_brand.tags.count(), len(self.tags) + 1)
        self.assertEqual(
            updated_brand.tags.filter(
                name__in=list(map(lambda tag_: tag_['name'], [*self.tags_as_dicts, self.other_tag]))
            ).count(),
            len(self.tags) + 1
        )
        self.assertEqual(updated_brand.tags.filter(is_other=True).count(), 1)

        # check formats
        self.assertEqual(updated_brand.formats.count(), len(self.formats) + 1)
        self.assertEqual(
            updated_brand.formats.filter(
                name__in=list(map(lambda format_: format_['name'], [*self.formats_as_dicts, self.other_format]))
            ).count(),
            len(self.formats) + 1
        )
        self.assertEqual(updated_brand.formats.filter(is_other=True).count(), 1)

        # check goals
        self.assertEqual(updated_brand.goals.count(), len(self.goals) + 1)
        self.assertEqual(
            updated_brand.goals.filter(
                name__in=list(map(lambda goal: goal['name'], [*self.goals_as_dicts, self.other_goal]))
            ).count(),
            len(self.goals) + 1
        )
        self.assertEqual(updated_brand.goals.filter(is_other=True).count(), 1)

        # check categories of interest
        self.assertEqual(updated_brand.categories_of_interest.count(), len(self.categories_of_interest) + 1)
        self.assertEqual(
            updated_brand.categories_of_interest.filter(name__in=list(
                map(lambda cat: cat['name'], [*self.categories_of_interest_as_dicts, self.other_category_of_interest]))
            ).count(),
            len(self.categories_of_interest) + 1
        )
        self.assertEqual(updated_brand.categories_of_interest.filter(is_other=True).count(), 1)

        # check business groups
        self.assertEqual(updated_brand.business_groups.count(), len(self.new_business_groups))
        self.assertEqual(
            updated_brand.business_groups.filter(name__in=self.new_business_groups).count(),
            len(self.new_business_groups)
        )

        # check target audience
        self.assertIsNotNone(updated_brand.target_audience)
        self.assertIsNotNone(updated_brand.target_audience.age)
        self.assertIsNotNone(updated_brand.target_audience.gender)
        self.assertIsNotNone(updated_brand.target_audience.income)
        self.assertEqual(updated_brand.target_audience.age.men, self.age['men'])
        self.assertEqual(updated_brand.target_audience.age.women, self.age['women'])
        self.assertEqual(updated_brand.target_audience.gender.men, self.gender['men'])
        self.assertEqual(updated_brand.target_audience.gender.women, self.gender['women'])
        self.assertEqual(updated_brand.target_audience.income, self.target_audience['income'])
        self.assertEqual(updated_brand.target_audience.geos.count(), len(self.geos))
        self.assertEqual(updated_brand.target_audience.geos.filter(self.geos_query).count(), len(self.geos))

        user_directory_path = os.path.join(settings.MEDIA_ROOT, f'user_{self.user.pk}')

        # check single photos
        filenames = default_storage.listdir(user_directory_path)[1]
        logo_files = list(filter(lambda name: name.startswith('logo'), filenames))
        photo_files = list(filter(lambda name: name.startswith('photo'), filenames))

        self.assertEqual(len(logo_files), 1)
        self.assertEqual(len(photo_files), 1)

        # check that files actually changed by comparing their sizes
        self.assertEqual(
            default_storage.size(os.path.join(user_directory_path, logo_files[0])), self.new_image_size
        )
        self.assertEqual(
            default_storage.size(os.path.join(user_directory_path, photo_files[0])), self.new_image_size
        )

        # check gallery
        gallery_path = os.path.join(user_directory_path, 'gallery')
        filenames = default_storage.listdir(gallery_path)[1]
        gallery_photos_expected = (
                self.initial_gallery_photos_num + len(self.gallery_add) - len(self.gallery_remove)
        )

        self.assertEqual(len(filenames), gallery_photos_expected)
        self.assertEqual(updated_brand.gallery_photos.count(), gallery_photos_expected)

        for name in filenames:
            # check that files actually changed by comparing their sizes
            self.assertEqual(default_storage.size(os.path.join(gallery_path, name)), self.new_image_size)

        # check product photos
        product_photos_path = os.path.join(user_directory_path, 'product_photos')
        match_photos_path = os.path.join(product_photos_path, 'match')
        card_photos_path = os.path.join(product_photos_path, 'brand_card')
        match_filenames = default_storage.listdir(match_photos_path)[1]
        card_filenames = default_storage.listdir(card_photos_path)[1]

        for name in match_filenames:
            # check that files actually changed by comparing their sizes
            self.assertEqual(default_storage.size(os.path.join(match_photos_path, name)), self.new_image_size)

        for name in card_filenames:
            # check that files actually changed by comparing their sizes
            self.assertEqual(default_storage.size(os.path.join(card_photos_path, name)), self.new_image_size)

        match_photos_expected = (
                self.initial_match_photos_num
                + len(self.product_photos_match_add)
                - len(self.product_photos_match_remove)
        )

        card_photos_expected = (
                self.initial_card_photos_num
                + len(self.product_photos_card_add)
                - len(self.product_photos_card_remove)
        )

        self.assertEqual(len(match_filenames), match_photos_expected)
        self.assertEqual(len(card_filenames), card_photos_expected)
        self.assertEqual(updated_brand.product_photos.count(), match_photos_expected + card_photos_expected)
        self.assertEqual(updated_brand.product_photos.filter(format=ProductPhoto.MATCH).count(), match_photos_expected)
        self.assertEqual(updated_brand.product_photos.filter(format=ProductPhoto.CARD).count(), card_photos_expected)

    def test_brand_update_gallery_photos_can_remove_all(self):
        response = self.auth_client.patch(self.url, {
            'gallery_remove': json.dumps(self.gallery_remove)
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.brand.gallery_photos.exists())
        self.assertEqual(len(glob.glob(os.path.join(settings.MEDIA_ROOT, f'user_{self.user.id}', 'gallery', '*'))), 0)

    def test_brand_update_target_audience_remove_fields(self):
        response = self.auth_client.patch(self.url, {
            'target_audience': json.dumps({
                "age": {},
                "gender": {},
                "geos": [],
                "income": None
            })
        })

        updated_brand = Brand.objects.select_related(
            'target_audience__age',
            'target_audience__gender'
        ).get(pk=self.brand.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(updated_brand.target_audience)
        self.assertIsNone(updated_brand.target_audience.age)
        self.assertIsNone(updated_brand.target_audience.gender)
        self.assertIsNone(updated_brand.target_audience.income)
        self.assertFalse(Age.objects.filter(target_audience=updated_brand.target_audience).exists())
        self.assertFalse(Gender.objects.filter(target_audience=updated_brand.target_audience).exists())
        self.assertFalse(updated_brand.target_audience.geos.all().exists())

    def test_brand_update_existing_target_audience(self):
        response = self.auth_client.patch(self.url, {'target_audience': json.dumps(self.target_audience)})

        updated_brand = Brand.objects.select_related(
            'target_audience__age',
            'target_audience__gender'
        ).get(pk=self.brand.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(updated_brand.target_audience.age.men, self.age['men'])
        self.assertEqual(updated_brand.target_audience.age.women, self.age['women'])
        self.assertEqual(Age.objects.filter(target_audience=updated_brand.target_audience).count(), 1)

        self.assertEqual(updated_brand.target_audience.gender.men, self.gender['men'])
        self.assertEqual(updated_brand.target_audience.gender.women, self.gender['women'])
        self.assertEqual(Gender.objects.filter(target_audience=updated_brand.target_audience).count(), 1)

        self.assertEqual(updated_brand.target_audience.income, self.target_audience['income'])

        expected_geos = len(self.geos)
        self.assertEqual(updated_brand.target_audience.geos.count(), expected_geos)
        self.assertEqual(updated_brand.target_audience.geos.filter(self.geos_query).count(), expected_geos)

    def test_brand_update_cannot_remove_all_tags(self):
        response = self.auth_client.patch(self.url, {
            'tags': json.dumps([])
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_brand_update_can_remove_all_to_many_fields_except_tags_and_photos(self):
        response = self.auth_client.patch(self.url, {
            'goals': json.dumps([]),
            'formats': json.dumps([]),
            'categories_of_interest': json.dumps([]),
            'new_blogs': json.dumps([]),
            'new_business_groups': json.dumps([])
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(self.brand.goals.exists())
        self.assertFalse(self.brand.formats.exists())
        self.assertFalse(self.brand.categories_of_interest.exists())
        self.assertFalse(self.brand.blogs.exists())
        self.assertFalse(self.brand.business_groups.exists())

    def test_brand_update_fields_with_other_option(self):
        self.brand.category = CategoryFactory(is_other=True)
        self.brand.save()
        self.brand.tags.set([TagFactory(is_other=True)])
        self.brand.formats.set([FormatFactory(is_other=True)])
        self.brand.goals.set([GoalFactory(is_other=True)])
        self.brand.categories_of_interest.set([CategoryFactory(is_other=True)])

        categories_before = int(Category.objects.count())
        formats_before = int(Format.objects.count())
        goals_before = int(Goal.objects.count())
        tags_before = int(Tag.objects.count())

        other_category = factory.build(dict, FACTORY_CLASS=CategoryFactory, is_other=True)
        data = {
            'category': json.dumps(other_category),
            'tags': self.update_data['tags'],
            'formats': self.update_data['formats'],
            'goals': self.update_data['goals'],
            'categories_of_interest': self.update_data['categories_of_interest']
        }

        response = self.auth_client.patch(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated_brand = Brand.objects.select_related('category').get(pk=self.brand.pk)

        # check category
        self.assertEqual(categories_before, Category.objects.count())
        self.assertEqual(updated_brand.category.name, other_category['name']),
        self.assertTrue(updated_brand.category.is_other)
        self.assertEqual(Category.objects.filter(brands__in=[self.brand.pk], is_other=True).count(), 1)

        # check tags
        self.assertEqual(tags_before, Tag.objects.count())
        self.assertEqual(updated_brand.tags.count(), len(self.tags) + 1)

        tag_query = Q()
        for tag_ in [*self.tags_as_dicts, self.other_tag]: tag_query |= Q(**tag_)
        self.assertEqual(updated_brand.tags.filter(tag_query).count(), len(self.tags) + 1)

        # check formats
        self.assertEqual(formats_before, Format.objects.count())
        self.assertEqual(updated_brand.formats.count(), len(self.formats) + 1)

        format_query = Q()
        for format_ in [*self.formats_as_dicts, self.other_format]: format_query |= Q(**format_)
        self.assertEqual(updated_brand.formats.filter(format_query).count(), len(self.formats) + 1)

        # check goals
        self.assertEqual(goals_before, Goal.objects.count())
        self.assertEqual(updated_brand.goals.count(), len(self.goals) + 1)

        goals_query = Q()
        for goal in [*self.goals_as_dicts, self.other_goal]: goals_query |= Q(**goal)
        self.assertEqual(updated_brand.goals.filter(goals_query).count(), len(self.goals) + 1)

        # check categories of interest
        self.assertEqual(updated_brand.categories_of_interest.count(), len(self.categories_of_interest) + 1)

        categories_of_interest_query = Q()
        for cat in [*self.categories_of_interest_as_dicts, self.other_category_of_interest]:
            categories_of_interest_query |= Q(**cat)

        self.assertEqual(
            updated_brand.categories_of_interest.filter(categories_of_interest_query).count(),
            len(self.categories_of_interest) + 1
        )
