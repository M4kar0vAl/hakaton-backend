from datetime import timedelta

from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category
from core.apps.payments.models import Tariff, GiftPromoCode

User = get_user_model()


class GiftPromoCodeListTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email=f'user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

        country = Country.objects.create(name='Country', continent='EU')
        city = City.objects.create(name='City', country=country)

        brand_data = cls.brand_data = {
            'tg_nickname': '@asfhbnaf',
            'city': city,
            'name': 'brand1',
            'position': 'position',
            'category': Category.objects.get(id=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        cls.brand = Brand.objects.create(user=cls.user, **brand_data)

        cls.lite_tariff = Tariff.objects.get(name='Lite Match')

        GiftPromoCode.objects.bulk_create([
            # valid
            GiftPromoCode(
                tariff_id=cls.lite_tariff.id,
                expires_at=timezone.now() + timedelta(days=1),
                giver=cls.brand
            ),
            # used
            GiftPromoCode(
                tariff_id=cls.lite_tariff.id,
                expires_at=timezone.now() + timedelta(days=1),
                giver=cls.brand,
                is_used=True
            ),
            # expired
            GiftPromoCode(
                tariff_id=cls.lite_tariff.id,
                expires_at=timezone.now() - timedelta(days=1),
                giver=cls.brand
            )
        ])

        cls.url = reverse('gift_promocodes-list')

    def test_list_gift_promocodes_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_gift_promocodes_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email=f'user2@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_gift_promocodes(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_gift_promocodes_excludes_already_used_gifts(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_gift_promocodes_excludes_expired_gifts(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_gift_promocodes_returns_only_current_brand_codes(self):
        another_user = User.objects.create_user(
            email=f'another_user@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        another_brand = Brand.objects.create(user=another_user, **self.brand_data)

        GiftPromoCode.objects.create(
            tariff_id=self.lite_tariff.id,
            expires_at=timezone.now() + timedelta(days=1),
            giver=another_brand
        )

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
