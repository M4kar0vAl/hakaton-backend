import json
import os
import shutil

from cities_light.models import City, Country
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.blacklist.models import BlackList
from core.apps.brand.models import Brand, Category, TargetAudience
from core.apps.chat.models import Room, RoomFavorites
from core.apps.payments.models import Tariff, Subscription

User = get_user_model()


@override_settings(MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'media', 'TEST'))
class BrandDeleteTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )
        cls.user_id = cls.user.id
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

        cls.country = Country.objects.create(name='Country', continent='EU')
        cls.city1 = City.objects.create(name='City1', country=cls.country)
        cls.city2 = City.objects.create(name='City2', country=cls.country)

    def setUp(self):
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
        gallery_photo1 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        gallery_photo2 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')

        data = {
            'tg_nickname': '@asfhbnaf',
            'blogs_list': json.dumps(["https://example.com", "https://example2.com"]),
            'city': self.city1.id,
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

        response = self.auth_client.post(reverse('brand-list'), data, format='multipart')
        self.brand = Brand.objects.get(id=response.data['id'])
        self.url = reverse('brand-me')

        update_data = {
            'mission_statement': 'mission_statement',
            'formats': json.dumps([
                {"name": "Продукт"},
                {"name": "other", "is_other": True}
            ]),
            'goals': json.dumps([
                {"name": "Продажи"},
                {"name": "other", "is_other": True}
            ]),
            'offline_space': 'offline_space',
            'problem_solving': 'problem_solving',
            'target_audience': json.dumps({
                "age": {"men": 30, "women": 40},
                "gender": {"men": 30, "women": 70},
                "geos": [
                    {"city": self.city1.id, "people_percentage": 40},
                    {"city": self.city2.id, "people_percentage": 60}
                ],
                "income": 50000
            }),
            'categories_of_interest': json.dumps([
                {"name": "HoReCa"},
                {"name": "Kids"},
                {"name": "other", "is_other": True}
            ]),
            'new_business_groups': json.dumps(["name", "https://example.com"]),
            'gallery_add': [gallery_photo1, gallery_photo2]
        }

        self.auth_client.patch(self.url, update_data, format='multipart')

        # add subscription to brand
        self.tariff = Tariff.objects.get(name='Lite Match')
        now = timezone.now()

        Subscription.objects.create(
            brand=self.brand,
            tariff=self.tariff,
            start_date=now,
            end_date=now + relativedelta(months=self.tariff.duration.days // 30),
            is_active=True
        )

    def tearDown(self):
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT))

    def test_brand_delete_unauthenticated_not_allowed(self):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_brand_delete_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user2@example.com',
            phone='+79993332212',
            fullname='Юзеров Юзер1 Юзерович',
            password='Pass!234',
            is_active=True
        )
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_brand_delete(self):
        another_user = User.objects.create_user(
            email='another_user@example.com',
            phone='+79993332212',
            fullname='Юзеров Юзер1 Юзерович',
            password='Pass!234',
            is_active=True
        )

        brand_data = {
            'tg_nickname': '@asfhbnaf',
            'name': 'brand1',
            'position': 'position',
            'category': Category.objects.get(pk=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        another_brand = Brand.objects.create(user=another_user, **brand_data)

        # initial brand and another brand block each other
        bl1, bl2 = BlackList.objects.bulk_create([
            BlackList(initiator=self.brand, blocked=another_brand),
            BlackList(initiator=another_brand, blocked=self.brand),
        ])

        rooms = Room.objects.bulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT),
            Room(type=Room.SUPPORT),
        ])

        fav1, fav2, fav3 = RoomFavorites.objects.bulk_create([
            RoomFavorites(user=self.user, room=room)
            for room in rooms
        ])

        response = self.auth_client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        deleted_brand = Brand.objects.get(id=self.brand.id)

        self.assertIsNone(deleted_brand.user)
        self.assertIsNotNone(deleted_brand.city)

        # check that subscriptions remained but were deactivated
        self.assertEqual(deleted_brand.subscriptions.count(), 1)
        self.assertFalse(deleted_brand.subscriptions.filter(is_active=True).exists())

        # check that blacklist was cleared
        self.assertFalse(BlackList.objects.filter(id__in=[bl1.id, bl2.id]).exists())

        # check that favorite rooms were cleared
        self.assertFalse(RoomFavorites.objects.filter(pk__in=[fav1.pk, fav2.pk, fav3.pk]).exists())

        # check that target audience remains
        self.assertIsNotNone(deleted_brand.target_audience)

        # check common fields
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
            self.assertEqual(getattr(deleted_brand, field), '')

        # check target audience
        self.assertTrue(TargetAudience.objects.filter(brand=self.brand).exists())

        # check that unnecessary objects were deleted
        self.assertFalse(deleted_brand.blogs.exists())
        self.assertFalse(deleted_brand.business_groups.exists())
        self.assertFalse(deleted_brand.product_photos.exists())
        self.assertFalse(deleted_brand.gallery_photos.exists())

        # check user media directory
        self.assertFalse(default_storage.exists(os.path.join(settings.MEDIA_ROOT, f'user_{self.user_id}')))
