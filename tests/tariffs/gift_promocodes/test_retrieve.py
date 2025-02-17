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


class GiftPromoCodeRetrieveTestCase(APITestCase):
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

        cls.brand_data = {
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

        cls.brand = Brand.objects.create(user=cls.user, **cls.brand_data)

        cls.lite_tariff = Tariff.objects.get(name='Lite Match')
        now = timezone.now()

        gift_promocodes = GiftPromoCode.objects.bulk_create([
            # valid
            GiftPromoCode(
                tariff_id=cls.lite_tariff.id,
                expires_at=now + timedelta(days=1),
                giver=cls.brand
            ),
            # used
            GiftPromoCode(
                tariff_id=cls.lite_tariff.id,
                expires_at=now + timedelta(days=1),
                giver=cls.brand,
                is_used=True
            ),
            # expired
            GiftPromoCode(
                tariff_id=cls.lite_tariff.id,
                expires_at=now - timedelta(days=1),
                giver=cls.brand
            )
        ])

        cls.valid_gift = gift_promocodes[0]
        cls.used_gift = gift_promocodes[1]
        cls.expired_gift = gift_promocodes[2]

        cls.valid_gift_url = reverse('gift_promocodes-detail', args=[cls.valid_gift.code])
        cls.used_gift_url = reverse('gift_promocodes-detail', args=[cls.used_gift.code])
        cls.expired_gift_url = reverse('gift_promocodes-detail', args=[cls.expired_gift.code])

    def test_retrieve_gift_promocode_unauthenticated_now_allowed(self):
        response = self.client.get(self.valid_gift_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_gift_promocode_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email=f'user2@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.get(self.valid_gift_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_gift_promocode_already_used(self):
        response = self.auth_client.get(self.used_gift_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_gift_promocode_expired(self):
        response = self.auth_client.get(self.expired_gift_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_gift_promocode(self):
        response = self.auth_client.get(self.valid_gift_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.valid_gift.id)

    def test_retrieve_gift_promocode_by_another_brand(self):
        another_user = User.objects.create_user(
            email=f'another_user@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        Brand.objects.create(user=another_user, **self.brand_data)

        another_auth_client = APIClient()
        another_auth_client.force_authenticate(another_user)

        response = another_auth_client.get(self.valid_gift_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
