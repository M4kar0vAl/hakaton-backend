import json
import os

import factory
from django.conf import settings
from django.core.files.storage import default_storage
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import (
    ProductPhotoFactory,
    CategoryFactory,
    BlogFactory,
    BrandPartOneFactory,
    TagFactory,
    BrandShortFactory
)
from core.apps.brand.models import ProductPhoto, Brand, Tag, Blog
from core.apps.cities.factories import CityFactory


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class BrandCreateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

        cls.data = factory.build(
            dict,
            FACTORY_CLASS=BrandPartOneFactory,
            user=None,
            blogs=None,
            product_photos=None,
            category=None,
            city=None,
        )

        del cls.data['user']
        del cls.data['blogs']
        del cls.data['product_photos']

        cls.city = CityFactory()
        cls.category = CategoryFactory()

        blogs_data = factory.build_batch(dict, size=2, FACTORY_CLASS=BlogFactory)
        cls.blogs = list(map(lambda x: x['blog'], blogs_data))

        product_photos = factory.build_batch(dict, size=4, FACTORY_CLASS=ProductPhotoFactory)
        cls.product_photos_match = list(
            map(lambda x: x['image'], filter(lambda x: x['format'] == ProductPhoto.MATCH, product_photos))
        )
        cls.product_photos_card = list(
            map(lambda x: x['image'], filter(lambda x: x['format'] == ProductPhoto.CARD, product_photos))
        )

        cls.tags = TagFactory.create_batch(4)
        cls.tags_as_dicts = list(map(lambda tag: {'name': tag.name}, cls.tags))
        cls.other_tag = factory.build(dict, FACTORY_CLASS=TagFactory, is_other=True)

        cls.data['city'] = cls.city.pk
        cls.data['category'] = json.dumps({'name': cls.category.name})
        cls.data['blogs_list'] = json.dumps(cls.blogs)
        cls.data['product_photos_match'] = cls.product_photos_match
        cls.data['product_photos_card'] = cls.product_photos_card
        cls.data['tags'] = json.dumps([*cls.tags_as_dicts, cls.other_tag])

        cls.url = reverse('brand-list')

    def tearDown(self):
        # need to manually clear inMemoryStorage after every test
        default_storage.delete(os.path.join(settings.MEDIA_ROOT, f'user_{self.user.id}'))

    def test_create_brand_as_unauthenticated(self):
        response = self.client.post(self.url, {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_brand_with_valid_data(self):
        response = self.auth_client.post(self.url, self.data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user_id = response.data['user']['id']
        brand_id = response.data['id']

        self.assertTrue(Brand.objects.filter(user=self.user).exists())  # check that brand was created in db
        self.assertEqual(Blog.objects.filter(blog__in=self.blogs).count(), 2)

        # check that tags were created and assigned
        self.assertEqual(Tag.objects.filter(is_other=True).count(), 1)
        self.assertEqual(Brand.tags.through.objects.filter(brand_id=brand_id).count(), len(self.tags) + 1)

        # check that photos were uploaded
        self.assertTrue(default_storage.exists(os.path.join(f'user_{user_id}', 'logo.jpg')))
        self.assertTrue(default_storage.exists(os.path.join(f'user_{user_id}', 'photo.jpg')))

        self.assertEqual(len(default_storage.listdir(
            os.path.join(settings.MEDIA_ROOT, f'user_{user_id}', 'product_photos', 'match')
        )[1]), len(self.product_photos_match))
        self.assertEqual(len(default_storage.listdir(
            os.path.join(settings.MEDIA_ROOT, f'user_{user_id}', 'product_photos', 'brand_card')
        )[1]), len(self.product_photos_card))

        # check that product photos were created in db
        self.assertEqual(ProductPhoto.objects.filter(brand_id=brand_id).count(), 4)

    def test_create_brand_with_invalid_data(self):
        invalid_data = {}
        response = self.auth_client.post(self.url, invalid_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_brand_if_already_exists(self):
        BrandShortFactory(user=self.user)
        response = self.auth_client.post(self.url, self.data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
