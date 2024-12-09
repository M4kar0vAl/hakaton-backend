from datetime import timedelta

from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.apps.brand.models import Brand, Category
from core.apps.payments.models import PromoCode, GiftPromoCode

User = get_user_model()


class PromoCodeGetTestCase(APITestCase):
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

        now = timezone.now()
        cls.promocode = PromoCode.objects.create(code='test', discount=5, expires_at=now + timedelta(days=30))

        cls.url = reverse('promocode-detail', args=[cls.promocode.code])
        cls.subscribe_url = reverse('tariffs-subscribe')

    def test_check_promocode_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_check_promocode_wo_brand_not_allowed(self):
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

    def test_get_promocode(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_promocode_does_not_exist(self):
        response = self.auth_client.get(reverse('promocode-detail', args=['not_existing']))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_promocode_already_used_in_subscription(self):
        self.auth_client.post(self.subscribe_url, {'tariff': 2, 'promocode': self.promocode.id})

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_promocode_already_used_in_gift(self):
        # create gift with promo code
        GiftPromoCode.objects.create(
            tariff_id=2,
            expires_at=timezone.now() + timedelta(days=1),
            giver=self.brand,
            promocode=self.promocode
        )

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
