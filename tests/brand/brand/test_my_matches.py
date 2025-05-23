from django.contrib.auth import get_user_model
from django.test import tag
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category
from core.apps.payments.models import Subscription, Tariff
from tests.mixins import AssertNumQueriesLessThanMixin

User = get_user_model()


class BrandMyMatchesTestCase(
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

        cls.business_tariff = Tariff.objects.get(name='Business Match')
        cls.business_tariff_relativedelta = cls.business_tariff.get_duration_as_relativedelta()
        now = timezone.now()

        Subscription.objects.create(
            brand=cls.brand1,
            tariff=cls.business_tariff,
            start_date=now,
            end_date=now + cls.business_tariff_relativedelta,
            is_active=True
        )

        Subscription.objects.create(
            brand=cls.brand2,
            tariff=cls.business_tariff,
            start_date=now,
            end_date=now + cls.business_tariff_relativedelta,
            is_active=True
        )

        Subscription.objects.create(
            brand=cls.brand3,
            tariff=cls.business_tariff,
            start_date=now,
            end_date=now + cls.business_tariff_relativedelta,
            is_active=True
        )

        cls.url = reverse('brand-my_matches')
        cls.like_url = reverse('brand-like')

    # TODO optimize this method
    def create_n_matches(self, n: int) -> APIClient:
        """
        Create n matches in db.

        Will be created:
         - n users
         - n brands

        Also: 2n times will be called 'like' action

        Returns:
            APIClient instance that have n matches associated with it
        """
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

        business_tariff = Tariff.objects.get(name='Business Match')
        business_tariff_relativedelta = business_tariff.get_duration_as_relativedelta()
        now = timezone.now()

        Subscription.objects.bulk_create([
            Subscription(
                brand=brand,
                tariff=business_tariff,
                start_date=now,
                end_date=now + business_tariff_relativedelta,
                is_active=True
            )
            for brand in brands
        ])

        auth_clients = [APIClient() for _ in range(n + 1)]

        for i in range(n + 1):
            auth_clients[i].force_authenticate(users[i])

        client_to_return = auth_clients[0]
        brand = brands[0]

        for i in range(1, n + 1):
            client_to_return.post(self.like_url, {'target': brands[i].id})  # brand0 likes brandi
            auth_clients[i].post(self.like_url, {'target': brand.id})  # brandi likes brand0 MATCH

        return client_to_return

    def test_my_matches_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_matches_wo_brand_not_allowed(self):
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

    def test_my_matches_wo_active_sub_not_allowed(self):
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

    def test_my_matches_no_matches(self):
        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that returned list is empty
        self.assertFalse(response.data['results'])

    def test_my_matches(self):
        self.auth_client1.post(self.like_url, {'target': self.brand2.id})  # brand1 likes brand2
        match_response = self.auth_client2.post(self.like_url, {'target': self.brand1.id})  # brand2 likes brand1 MATCH

        client1_response = self.auth_client1.get(self.url)
        client2_response = self.auth_client2.get(self.url)

        self.assertEqual(client1_response.status_code, status.HTTP_200_OK)
        self.assertEqual(client2_response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(client1_response.data['results']), 1)
        self.assertEqual(len(client2_response.data['results']), 1)

        # check that both brands will receive each other
        self.assertEqual(client1_response.data['results'][0]['id'], self.brand2.id)
        self.assertEqual(client2_response.data['results'][0]['id'], self.brand1.id)

        # check that both brands will receive same room
        self.assertEqual(client1_response.data['results'][0]['match_room'], match_response.data['room'])
        self.assertEqual(client2_response.data['results'][0]['match_room'], match_response.data['room'])

    def test_my_matches_can_return_more_than_one_brand(self):
        self.auth_client1.post(self.like_url, {'target': self.brand2.id})  # brand1 likes brand2
        self.auth_client1.post(self.like_url, {'target': self.brand3.id})  # brand1 likes brand3
        self.auth_client2.post(self.like_url, {'target': self.brand1.id})  # brand2 likes brand1 MATCH
        self.auth_client3.post(self.like_url, {'target': self.brand1.id})  # brand3 likes brand1 MATCH

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 2)

    def test_my_matches_returns_matches_of_current_brand(self):
        self.auth_client1.post(self.like_url, {'target': self.brand2.id})  # brand1 likes brand2
        self.auth_client2.post(self.like_url, {'target': self.brand1.id})  # brand2 likes brand1 MATCH

        self.auth_client2.post(self.like_url, {'target': self.brand3.id})  # brand2 likes brand3
        self.auth_client3.post(self.like_url, {'target': self.brand2.id})  # brand3 likes brand2 MATCH

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 1)

    def test_my_matches_excludes_likes(self):
        self.auth_client1.post(self.like_url, {'target': self.brand2.id})  # brand1 likes brand2
        self.auth_client2.post(self.like_url, {'target': self.brand1.id})  # brand2 likes brand1 MATCH
        self.auth_client1.post(self.like_url, {'target': self.brand3.id})  # brand1 likes brand3

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 1)

    @tag('slow')
    def test_my_matches_number_of_queries(self):
        auth_client_50_matches = self.create_n_matches(50)

        with self.assertNumQueriesLessThan(6, verbose=True):
            response = auth_client_50_matches.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_my_matches_ordering(self):
        self.auth_client1.post(self.like_url, {'target': self.brand2.id})
        self.auth_client1.post(self.like_url, {'target': self.brand3.id})
        self.auth_client2.post(self.like_url, {'target': self.brand1.id})
        self.auth_client3.post(self.like_url, {'target': self.brand1.id})

        response = self.auth_client1.get(self.url)

        results = response.data['results']

        self.assertEqual(results[0]['id'], self.brand3.id)
        self.assertEqual(results[1]['id'], self.brand2.id)
