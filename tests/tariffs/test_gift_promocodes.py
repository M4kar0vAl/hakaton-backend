from datetime import timedelta

from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category
from core.apps.payments.models import Tariff, GiftPromoCode, PromoCode, Subscription

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

        gift_promocodes = GiftPromoCode.objects.bulk_create([
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

        now = timezone.now()
        cls.promocode = PromoCode.objects.create(code='test', discount=5, expires_at=now + timedelta(days=30))

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
