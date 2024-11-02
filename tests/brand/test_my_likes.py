from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import tag
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Category, Brand
from core.apps.payments.models import Subscription
from tests.mixins import AssertNumQueriesLessThanMixin

User = get_user_model()


class BrandMyLikesTestCase(
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

        brand_data = {
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

        # TODO change business sub definition
        cls.business_sub = Subscription.objects.create(name='Бизнес', cost=1000, duration=timedelta(days=180))

        cls.brand1 = Brand.objects.create(user=cls.user1, subscription=cls.business_sub, **brand_data)
        cls.brand2 = Brand.objects.create(user=cls.user2, **brand_data)
        cls.brand3 = Brand.objects.create(user=cls.user3, subscription=cls.business_sub, **brand_data)

        cls.url = reverse('brand-my_likes')
        cls.like_url = reverse('brand-like')
        cls.instant_coop_url = reverse('brand-instant-coop')

    def create_n_likes(self, n: int) -> APIClient:
        users = User.objects.bulk_create([User(
            email=f'trash_user{i}@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        ) for i in range(n + 1)])

        category = Category.objects.get(pk=1)

        brand_data = {
            'tg_nickname': '@asfhbnaf',
            'name': 'brand1',
            'position': 'position',
            'category': category,
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

        brands = Brand.objects.bulk_create([Brand(user=user, **brand_data) for user in users])

        client = APIClient()
        client.force_authenticate(users[0])

        for brand in brands[1:]:
            client.post(self.like_url, {'target': brand.id})

        return client

    def test_my_likes_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_likes_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user4@example.com',
            phone='+79993332214',
            fullname='Юзеров Юзер3 Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_likes_no_likes(self):
        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that returned list is empty
        self.assertFalse(response.data)

    def test_my_likes_no_instant_coops(self):
        self.auth_client1.post(self.like_url, {'target': self.brand2.id})  # brand1 likes brand2
        response = self.auth_client1.get(self.url)  # get brands that were liked by brand1

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that there is only one brand that was liked by brand1
        self.assertEqual(len(response.data), 1)

        # check that there is no instant room for these brands
        self.assertIsNone(response.data[0]['instant_room'])

    def test_my_likes_with_instant_coop(self):
        self.auth_client1.post(self.like_url, {'target': self.brand2.id})  # brand1 likes brand2

        # brand1 instant coops brand2, INSTANT room is created
        instant_coop_resp = self.auth_client1.post(self.instant_coop_url, {'target': self.brand2.id})

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that instant room is not None
        self.assertIsNotNone(response.data[0]['instant_room'])

        self.assertEqual(response.data[0]['instant_room'], instant_coop_resp.data['id'])

    def test_my_likes_includes_only_likes_of_current_brand(self):
        self.auth_client1.post(self.like_url, {'target': self.brand2.id})  # brand1 likes brand2
        self.auth_client3.post(self.like_url, {'target': self.brand1.id})  # brand3 likes brand1

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that there is only 1 liked brand
        self.assertEqual(len(response.data), 1)

    def test_my_likes_exclude_matches(self):
        self.auth_client1.post(self.like_url, {'target': self.brand2.id})  # brand1 likes brand2
        self.auth_client2.post(self.like_url, {'target': self.brand1.id})  # brand2 likes brand1 MATCH

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that response is empty
        self.assertFalse(response.data)

    def test_my_likes_can_return_more_than_one_brand(self):
        self.auth_client1.post(self.like_url, {'target': self.brand2.id})  # brand1 likes brand2
        self.auth_client1.post(self.like_url, {'target': self.brand3.id})  # brand1 likes brand3
        self.auth_client1.post(self.instant_coop_url, {'target': self.brand2.id})  # brand 1 instant coops brand2

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 2)

    @tag('slow')
    def test_number_of_queries_less_than_7(self):
        client = self.create_n_likes(50)

        with self.assertNumQueriesLessThan(7, verbose=True):
            response = client.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
