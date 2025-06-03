import os
import shutil

from django.conf import settings
from django.core.files.storage import default_storage
from django.test import override_settings, tag
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.models import BlackList
from core.apps.brand.factories import BrandFactory, BrandShortFactory
from core.apps.brand.models import Brand
from core.apps.chat.factories import RoomFavoritesFactory
from core.apps.chat.models import RoomFavorites
from core.apps.payments.models import Tariff, Subscription


@override_settings(MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'media', 'TEST'))
@tag('slow')
class BrandDeleteTestCase(APITransactionTestCase):  # django-cleanup requires TransactionTestCase to be used
    serialized_rollback = True

    def setUp(self):
        self.user = UserFactory()
        self.auth_client = APIClient()
        self.auth_client.force_authenticate(self.user)

        self.brand = BrandFactory(user=self.user)

        # add subscription to brand
        self.tariff = Tariff.objects.get(name='Lite Match')
        self.tariff_relativedelta = self.tariff.get_duration_as_relativedelta()
        now = timezone.now()

        Subscription.objects.create(
            brand=self.brand,
            tariff=self.tariff,
            start_date=now,
            end_date=now + self.tariff_relativedelta,
            is_active=True
        )

        self.url = reverse('brand-me')

    def tearDown(self):
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT))

    def test_brand_delete_unauthenticated_not_allowed(self):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_brand_delete_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_brand_delete(self):
        another_brand = BrandShortFactory()

        # initial brand and another brand block each other
        bl1, bl2 = BlackList.objects.bulk_create([
            BlackList(initiator=self.brand, blocked=another_brand),
            BlackList(initiator=another_brand, blocked=self.brand),
        ])

        fav1, fav2, fav3 = RoomFavoritesFactory.create_batch(3, user=self.user)

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

        # check that unnecessary objects were deleted
        self.assertFalse(deleted_brand.blogs.exists())
        self.assertFalse(deleted_brand.business_groups.exists())
        self.assertFalse(deleted_brand.product_photos.exists())
        self.assertFalse(deleted_brand.gallery_photos.exists())

        # check user media directory
        self.assertFalse(default_storage.exists(os.path.join(settings.MEDIA_ROOT, f'user_{self.user.pk}')))
