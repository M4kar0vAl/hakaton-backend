from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.blacklist.models import BlackList
from core.apps.brand.models import Category, Brand
from core.apps.payments.models import Tariff, Subscription
from tests.mixins import AssertNumQueriesLessThanMixin

User = get_user_model()


class LikedByTestCase(
    APITestCase,
    AssertNumQueriesLessThanMixin
):
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

        cls.brand_data = {
            'tg_nickname': '@asfhbnaf',
            'name': 'brand1',
            'position': 'position',
            'category': Category.objects.get(pk=1),
            'inst_url': 'https://example.com',
            'vk_url': 'https://example.com',
            'tg_url': 'https://example.com',
            'wb_url': 'https://example.com',
            'lamoda_url': 'https://example.com',
            'site_url': 'https://example.com',
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        cls.brand1 = Brand.objects.create(user=cls.user1, **cls.brand_data)
        cls.brand2 = Brand.objects.create(user=cls.user2, **cls.brand_data)
        cls.brand3 = Brand.objects.create(user=cls.user3, **cls.brand_data)

        cls.tariff = Tariff.objects.get(name='Business Match')
        now = timezone.now()

        Subscription.objects.create(
            brand=cls.brand1,
            tariff=cls.tariff,
            start_date=now,
            end_date=now + relativedelta(months=cls.tariff.duration.days // 30),
            is_active=True
        )

        Subscription.objects.create(
            brand=cls.brand2,
            tariff=cls.tariff,
            start_date=now,
            end_date=now + relativedelta(months=cls.tariff.duration.days // 30),
            is_active=True
        )

        Subscription.objects.create(
            brand=cls.brand3,
            tariff=cls.tariff,
            start_date=now,
            end_date=now + relativedelta(months=cls.tariff.duration.days // 30),
            is_active=True
        )

        cls.like_url = reverse('brand-like')
        cls.url = reverse('brand-liked_by')

    def test_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_without_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user4@example.com',
            phone='+79993332214',
            fullname='Юзеров Юзер3 Юзерович',
            password='Pass!234',
            is_active=True
        )
        auth_client = APIClient()
        auth_client.force_authenticate(user_wo_brand)

        response = auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_liked_by_wo_active_sub_not_allowed(self):
        user_wo_active_sub = User.objects.create_user(
            email='user5@example.com',
            phone='+79993332214',
            fullname='Юзеров Юзер3 Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        Brand.objects.create(user=user_wo_active_sub, **self.brand_data)

        response = client_wo_active_sub.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_liked_by_returns_empty_list_if_no_likes(self):
        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['results'])

    def test_liked_by_returns_correct_list_of_brands(self):
        self.auth_client2.post(self.like_url, {'target': self.brand1.id})  # brand2 likes brand1
        self.auth_client2.post(self.like_url, {'target': self.brand3.id})  # brand2 likes brand3
        self.auth_client1.post(self.like_url, {'target': self.brand3.id})  # brand1 likes brand3

        response = self.auth_client1.get(self.url)  # get who liked brand1

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.brand2.id)

    def test_liked_by_excludes_matches(self):
        self.auth_client2.post(self.like_url, {'target': self.brand1.id})  # brand2 likes brand1
        self.auth_client3.post(self.like_url, {'target': self.brand1.id})  # brand3 likes brand1
        self.auth_client1.post(self.like_url, {'target': self.brand3.id})  # brand1 likes brand3 MATCH!

        response = self.auth_client1.get(self.url)  # get who liked brand1

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 1)

    def test_liked_by_excludes_blacklist(self):
        self.auth_client2.post(self.like_url, {'target': self.brand1.id})  # brand2 likes brand1
        self.auth_client3.post(self.like_url, {'target': self.brand1.id})  # brand3 likes brand1

        BlackList.objects.bulk_create([
            BlackList(initiator=self.brand2, blocked=self.brand1),  # brand2 blocks brand1
            BlackList(initiator=self.brand1, blocked=self.brand3),  # brand1 blocks brand3
        ])

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        # results must exclude both blocked brands and brands that blocked the current one
        self.assertEqual(len(results), 0)

    def test_liked_by_number_of_queries(self):
        self.auth_client2.post(self.like_url, {'target': self.brand1.id})
        self.auth_client3.post(self.like_url, {'target': self.brand1.id})

        with self.assertNumQueriesLessThan(3, verbose=True):
            response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_liked_by_ordering(self):
        self.auth_client2.post(self.like_url, {'target': self.brand1.id})
        self.auth_client3.post(self.like_url, {'target': self.brand1.id})

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        # results are ordered by the time of a like descending
        self.assertEqual(results[0]['id'], self.brand3.id)
        self.assertEqual(results[1]['id'], self.brand2.id)
