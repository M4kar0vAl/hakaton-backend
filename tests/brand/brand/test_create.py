import json
import os

from cities_light.models import Country, City
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.apps.brand.models import ProductPhoto, Brand, Tag, Blog

User = get_user_model()


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
        cls.user = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )
        cls.url = reverse('brand-list')
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

        cls.country = Country.objects.create(name='Country', continent='EU')
        cls.city = City.objects.create(name='City', country=cls.country)

    def tearDown(self):
        # need to manually clear inMemoryStorage after every test
        default_storage.delete(os.path.join(settings.MEDIA_ROOT, f'user_{self.user.id}'))

    def test_create_brand_as_unauthenticated(self):
        response = self.client.post(self.url, {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_brand_with_valid_data(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01'
            b'\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        logo_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        photo_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file1 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file2 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file3 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')

        data = {
            'tg_nickname': '@asfhbnaf',
            'blogs_list': json.dumps(["https://example.com", "https://example2.com"]),
            'city': self.city.id,
            'name': 'brand1',
            'position': 'position',
            'category': json.dumps({"name": "Fashion"}),
            'inst_url': 'https://example.com',
            'vk_url': 'https://example.com',
            'tg_url': 'https://example.com',
            'wb_url': 'https://example.com',
            'lamoda_url': 'https://example.com',
            'site_url': 'https://example.com',
            'subs_count': 10000,
            'avg_bill': 10000,
            'tags': json.dumps([
                {"name": "Свобода", "is_other": False},
                {"name": "Минимализм"},
                {"name": "Любовь"},
                {"name": "Самобытность"},
                {"name": "Активность"},
                {"name": "other", "is_other": True}
            ]),
            'uniqueness': 'uniqueness',
            'logo': logo_file,
            'photo': photo_file,
            'product_photos_match': [product_file, product_file1],
            'product_photos_card': [product_file2, product_file3]
        }

        response = self.auth_client.post(self.url, data, format='multipart')
        user_id = response.data['user']['id']
        brand_id = response.data['id']
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Brand.objects.filter(user=self.user).exists())  # check brand was created in db

        self.assertEqual(Blog.objects.filter(
            blog__in=['https://example.com', 'https://example2.com']
        ).count(), 2)

        # check that tags were created and assigned
        self.assertEqual(Tag.objects.filter(name='other', is_other=True).count(), 1)
        self.assertEqual(Brand.tags.through.objects.filter(brand_id=brand_id).count(), 6)

        # check that photos were uploaded
        self.assertTrue(default_storage.exists(os.path.join(f'user_{user_id}', 'logo.gif')))
        self.assertTrue(default_storage.exists(os.path.join(f'user_{user_id}', 'photo.gif')))

        self.assertEqual(len(default_storage.listdir(
            os.path.join(settings.MEDIA_ROOT, f'user_{user_id}', 'product_photos', 'match')
        )[1]), 2)
        self.assertEqual(len(default_storage.listdir(
            os.path.join(settings.MEDIA_ROOT, f'user_{user_id}', 'product_photos', 'brand_card')
        )[1]), 2)

        # check that product photos were created in db
        self.assertEqual(ProductPhoto.objects.filter(brand_id=brand_id).count(), 4)

    def test_create_brand_with_invalid_data(self):
        invalid_data = {}
        response = self.auth_client.post(self.url, invalid_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_brand_if_already_exists(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01'
            b'\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        logo_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        photo_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file1 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file2 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file3 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')

        data = {
            'tg_nickname': '@asfhbnaf',
            'blogs_list': json.dumps(["https://example.com", "https://example2.com"]),
            'city': self.city,
            'name': 'brand1',
            'position': 'position',
            'category': json.dumps({"name": "Fashion"}),
            'inst_url': 'https://example.com',
            'vk_url': 'https://example.com',
            'tg_url': 'https://example.com',
            'wb_url': 'https://example.com',
            'lamoda_url': 'https://example.com',
            'site_url': 'https://example.com',
            'subs_count': 10000,
            'avg_bill': 10000,
            'tags': json.dumps([
                {"name": "Свобода", "is_other": False},
                {"name": "Минимализм"},
                {"name": "Любовь"},
                {"name": "Самобытность"},
                {"name": "Активность"},
                {"name": "other", "is_other": True}
            ]),
            'uniqueness': 'uniqueness',
            'logo': logo_file,
            'photo': photo_file,
            'product_photos_match': [product_file, product_file1],
            'product_photos_card': [product_file2, product_file3]
        }

        self.auth_client.post(self.url, data, format='multipart')
        response = self.auth_client.post(self.url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
