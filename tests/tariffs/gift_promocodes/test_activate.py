from datetime import timedelta

from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category
from core.apps.payments.models import Tariff, GiftPromoCode, Subscription

User = get_user_model()


class GiftPromoCodeActivateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email=f'user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.user2 = User.objects.create_user(
            email=f'user2@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.giver_auth_client = APIClient()
        cls.receiver_auth_client = APIClient()
        cls.giver_auth_client.force_authenticate(cls.user1)
        cls.receiver_auth_client.force_authenticate(cls.user2)

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

        cls.giver_brand = Brand.objects.create(user=cls.user1, **brand_data)
        cls.receiver_brand = Brand.objects.create(user=cls.user2, **brand_data)

        cls.lite_tariff = Tariff.objects.get(name='Lite Match')
        cls.business_tariff = Tariff.objects.get(name='Business Match')

        gift_promocodes = GiftPromoCode.objects.bulk_create([
            # valid lite
            GiftPromoCode(
                tariff_id=cls.lite_tariff.id,
                expires_at=timezone.now() + timedelta(days=1),
                giver=cls.giver_brand
            ),
            # valid business
            GiftPromoCode(
                tariff_id=cls.business_tariff.id,
                expires_at=timezone.now() + timedelta(days=1),
                giver=cls.giver_brand
            ),
            # used
            GiftPromoCode(
                tariff_id=cls.lite_tariff.id,
                expires_at=timezone.now() + timedelta(days=1),
                giver=cls.giver_brand,
                is_used=True
            ),
            # expired
            GiftPromoCode(
                tariff_id=cls.lite_tariff.id,
                expires_at=timezone.now() - timedelta(days=1),
                giver=cls.giver_brand
            )
        ])

        cls.valid_lite_gift = gift_promocodes[0]
        cls.valid_business_gift = gift_promocodes[1]
        cls.used_gift = gift_promocodes[2]
        cls.expired_gift = gift_promocodes[3]

        cls.url = reverse('gift_promocodes-activate')

    def test_activate_gift_promocode_unauthenticated_now_allowed(self):
        response = self.client.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_activate_gift_promocode_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email=f'user_wo_brand@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_activate_gift_promocode_with_active_subscription(self):
        Subscription.objects.create(
            brand=self.receiver_brand,
            tariff=self.lite_tariff,
            end_date=timezone.now() + timedelta(days=1),
            is_active=True
        )

        response = self.receiver_auth_client.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_gift_promocode_cannot_use_own_gift(self):
        response = self.giver_auth_client.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_gift_promocode_already_used(self):
        response = self.receiver_auth_client.post(self.url, {'gift_promocode': self.used_gift.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_gift_promocode_already_expired(self):
        response = self.receiver_auth_client.post(self.url, {'gift_promocode': self.expired_gift.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_gift_promocode(self):
        response = self.receiver_auth_client.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.receiver_brand.subscriptions.count(), 1)

        # check that subscription was bound to gift promo code
        self.assertEqual(self.receiver_brand.subscriptions.get().gift_promocode.id, self.valid_lite_gift.id)

        # check that correct tariff was applied
        self.assertEqual(response.data['tariff']['id'], self.valid_lite_gift.tariff_id)

        # check that promocode wasn't used
        self.assertIsNone(response.data['promocode'])

        # check that gifted subscription is activated
        self.assertTrue(response.data['is_active'])

    def test_activate_gift_promocode_cannot_activate_twice_same_gift(self):
        self.receiver_auth_client.post(self.url, {'gift_promocode': self.valid_lite_gift.id})
        response = self.receiver_auth_client.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check that gift promo code is marked as used
        self.assertTrue(GiftPromoCode.objects.get(id=self.valid_lite_gift.id).is_used)
