from datetime import timedelta

from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category
from core.apps.payments.models import Tariff, PromoCode, Subscription

User = get_user_model()


class GiftPromoCodeCreateTestCase(APITestCase):
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

        cls.trial_tariff = Tariff.objects.get(name='Trial')
        cls.lite_tariff = Tariff.objects.get(name='Lite Match')
        cls.business_tariff = Tariff.objects.get(name='Business Match')
        cls.business_tariff_relativedelta = cls.business_tariff.get_duration_as_relativedelta()

        now = timezone.now()
        cls.promocode = PromoCode.objects.create(code='test', discount=5, expires_at=now + timedelta(days=30))

        Subscription.objects.create(
            brand=cls.brand,
            tariff=cls.business_tariff,
            start_date=now,
            end_date=now + cls.business_tariff_relativedelta,
            is_active=True
        )

        cls.url = reverse('gift_promocodes-list')

    def test_create_gift_promocode_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'tariff': self.lite_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_gift_promocode_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email=f'user2@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.post(self.url, {'tariff': self.lite_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_gift_promocode_wo_active_sub_not_allowed(self):
        user_wo_active_sub = User.objects.create_user(
            email='user_wo_active_sub@example.com',
            phone='+79993332213',
            fullname='Юзеров Юзер2 Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        Brand.objects.create(user=user_wo_active_sub, **self.brand_data)

        response = client_wo_active_sub.post(self.url, {'tariff': self.lite_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_gift_promocode_cannot_gift_trial(self):
        response = self.auth_client.post(self.url, {'tariff': self.trial_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_gift_promocode_for_lite_tariff(self):
        response = self.auth_client.post(self.url, {'tariff': self.lite_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['promocode'])

    def test_create_gift_promocode_for_business_tariff(self):
        response = self.auth_client.post(self.url, {'tariff': self.business_tariff.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['promocode'])

    def test_create_gift_promocode_with_promocode(self):
        response = self.auth_client.post(self.url, {'tariff': self.lite_tariff.id, 'promocode': self.promocode.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['promocode'], self.promocode.id)

    def test_create_gift_promocode_if_promocode_already_used_in_gift(self):
        self.auth_client.post(self.url, {'tariff': self.business_tariff.id, 'promocode': self.promocode.id})
        response = self.auth_client.post(self.url, {'tariff': self.lite_tariff.id, 'promocode': self.promocode.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_gift_promocode_if_promocode_already_used_in_subscription(self):
        Subscription.objects.create(
            brand=self.brand,
            tariff=self.lite_tariff,
            end_date=timezone.now() + timedelta(days=1),
            promocode=self.promocode  # use promo code
        )

        response = self.auth_client.post(self.url, {
            'tariff': self.lite_tariff.id,
            'promocode': self.promocode.id  # try to use the same promo code
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
