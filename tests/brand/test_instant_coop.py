from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category, Match
from core.apps.chat.models import Room
from core.apps.payments.models import Subscription, Tariff

User = get_user_model()


class BrandInstantCooperationTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.user2 = User.objects.create_user(
            email='user2@example.com',
            phone='+79993332212',
            fullname='Юзеров Юзер1 Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.user3 = User.objects.create_user(
            email='user3@example.com',
            phone='+79993332213',
            fullname='Юзеров Юзер2 Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.auth_client1 = APIClient()
        cls.auth_client2 = APIClient()
        cls.auth_client3 = APIClient()

        cls.auth_client1.force_authenticate(cls.user1)
        cls.auth_client2.force_authenticate(cls.user2)
        cls.auth_client3.force_authenticate(cls.user3)

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

        cls.business_tariff = Tariff.objects.get(name='Business Match')
        cls.lite_tariff = Tariff.objects.get(name='Lite Match')

        now = timezone.now()

        # business sub and liked brand2
        cls.brand1 = Brand.objects.create(user=cls.user1, **brand_data)
        Subscription.objects.create(
            brand=cls.brand1,
            tariff=cls.business_tariff,
            start_date=now,
            end_date=now + relativedelta(months=cls.business_tariff.duration.days // 30),
            is_active=True
        )

        # without business sub, liked brand3
        cls.brand2 = Brand.objects.create(user=cls.user2, **brand_data)
        Subscription.objects.create(
            brand=cls.brand2,
            tariff=cls.lite_tariff,
            start_date=now,
            end_date=now + relativedelta(months=cls.lite_tariff.duration.days // 30),
            is_active=True
        )

        # business sub, without like
        cls.brand3 = Brand.objects.create(user=cls.user3, **brand_data)
        Subscription.objects.create(
            brand=cls.brand3,
            tariff=cls.business_tariff,
            start_date=now,
            end_date=now + relativedelta(months=cls.business_tariff.duration.days // 30),
            is_active=True
        )

        cls.url = reverse('brand-instant-coop')
        cls.like_url = reverse('brand-like')

        cls.like1_2_response = cls.auth_client1.post(cls.like_url, {'target': cls.brand2.id})  # brand1 like brand2
        cls.like2_3_response = cls.auth_client2.post(cls.like_url, {'target': cls.brand3.id})  # brand2 like brand3

    def test_instant_coop_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_instant_coop_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user4@example.com',
            phone='+79993332214',
            fullname='Юзеров Юзер3 Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instant_coop_wo_business_sub_not_allowed(self):
        response = self.auth_client2.post(self.url, {'target': self.brand3.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instant_coop_wo_like_not_allowed(self):
        response = self.auth_client3.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instant_coop(self):
        response = self.auth_client1.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check that room was created
        self.assertEqual(Room.objects.count(), 1)

        room = Room.objects.prefetch_related('participants').get(pk=response.data['id'])

        # check that room type is INSTANT
        self.assertEqual(room.type, Room.INSTANT)

        # check that users were added to room participants
        self.assertTrue(self.brand1.user in room.participants.all())
        self.assertTrue(self.brand2.user in room.participants.all())

        # check that instant room was assigned to like
        self.assertIsNotNone(room.match)
        self.assertEqual(room.match.id, self.like1_2_response.data['id'])

    def test_cannot_coop_with_the_same_brand(self):
        self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 instant coop brand2
        response = self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 instant coop brand2 AGAIN

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check that another room was not created
        self.assertEqual(Room.objects.count(), 1)

    def test_instant_coop_with_match_not_allowed(self):
        self.auth_client1.post(self.like_url, {'target': self.brand3.id})
        self.auth_client3.post(self.like_url, {'target': self.brand1.id})

        response = self.auth_client1.post(self.url, {'target': self.brand3.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
