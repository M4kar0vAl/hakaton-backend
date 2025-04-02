from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category, Match, Collaboration
from core.apps.brand.utils import get_periods
from core.apps.payments.models import Tariff, Subscription
from tests.mixins import AssertNumQueriesLessThanMixin

User = get_user_model()


class StatisticsTestCase(
    APITestCase,
    AssertNumQueriesLessThanMixin
):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

        cls.brand_data = {
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

        cls.brand = Brand.objects.create(user=cls.user, **cls.brand_data)

        cls.business_tariff = Tariff.objects.get(name='Business Match')
        cls.business_tariff_relativedelta = cls.business_tariff.get_duration_as_relativedelta()
        now = timezone.now()

        Subscription.objects.create(
            brand=cls.brand,
            tariff=cls.business_tariff,
            start_date=now,
            end_date=now + cls.business_tariff_relativedelta,
            is_active=True
        )

        cls.url = reverse('brand-statistics')
        cls.like_url = reverse('brand-like')
        cls.collab_url = reverse('collaboration')

    def test_statistics_unauthenticated_not_allowed(self):
        response = self.client.get(f'{self.url}?period=1')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_statistics_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user_wo_brand@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_brand = APIClient()
        client_wo_brand.force_authenticate(user_wo_brand)

        response = client_wo_brand.get(f'{self.url}?period=1')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_statistics_wo_active_sub_not_allowed(self):
        user_wo_active_sub = User.objects.create_user(
            email='user_wo_active_sub@example.com',
            phone='+79993332214',
            fullname='Юзеров Юзер3 Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        Brand.objects.create(user=user_wo_active_sub, **self.brand_data)

        response = client_wo_active_sub.get(f'{self.url}?period=1')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_statistics(self):
        users = User.objects.bulk_create([
            User(
                email=f'user_{i}@example.com',
                phone='+79993332211',
                fullname='Юзеров Юзер Юзерович',
                password='Pass!234',
                is_active=True
            )
            for i in range(3)
        ])

        brands = Brand.objects.bulk_create([
            Brand(**self.brand_data, user=user)
            for user in users
        ])

        clients = []

        for user in users:
            client = APIClient()
            client.force_authenticate(user)
            clients.append(client)

        brand1, brand2, brand3 = brands
        client1, client2, client3 = clients

        now = timezone.now()

        Subscription.objects.bulk_create([
            Subscription(
                brand=brand,
                tariff=self.business_tariff,
                start_date=now,
                end_date=now + self.business_tariff_relativedelta,
                is_active=True
            )
            for brand in brands
        ])

        self.auth_client.post(self.like_url, {'target': brand1.id})  # initial brand likes brand1
        self.auth_client.post(self.like_url, {'target': brand2.id})  # initial brand likes brand2
        self.auth_client.post(self.like_url, {'target': brand3.id})  # initial brand likes brand3

        match_response1 = client1.post(self.like_url, {'target': self.brand.id})  # brand1 likes initial MATCH
        match_response2 = client2.post(self.like_url, {'target': self.brand.id})  # brand2 likes initial MATCH

        collab_data = {
            "success_assessment": 10,
            "success_reason": "string",
            "to_improve": "string",
            "subs_received": 2147483647,
            "leads_received": 2147483647,
            "sales_growth": "string",
            "audience_reach": 2147483647,
            "bill_change": "string",
            "new_offers": True,
            "new_offers_comment": "string",
            "perception_change": True,
            "brand_compliance": 10,
            "platform_help": 5,
            "difficulties": True,
            "difficulties_comment": "string"
        }

        # initial brand reports about collab with brand1
        self.auth_client.post(self.collab_url, {**collab_data, 'match': match_response1.data['id']})

        # brand2 reports about collab with initial brand
        client2.post(self.collab_url, {**collab_data, 'match': match_response2.data['id']})

        response = self.auth_client.get(f'{self.url}?period=1')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['likes'], 3)
        self.assertEqual(response.data[0]['matches'], 2)
        self.assertEqual(response.data[0]['collabs'], 2)

    def test_statistics_period_query_param(self):
        # test period is not set
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test period is not a number
        response = self.auth_client.get(f'{self.url}?period=as')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test period is not in a valid range
        response = self.auth_client.get(f'{self.url}?period=0')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_statistics_periods(self):
        # create 12 users
        users = User.objects.bulk_create([
            User(
                email=f'user_{i}@example.com',
                phone='+79993332211',
                fullname='Юзеров Юзер Юзерович',
                password='Pass!234',
                is_active=True
            )
            for i in range(12)
        ])

        # create 12 brands for users
        brands = Brand.objects.bulk_create([
            Brand(**self.brand_data, user=user)
            for user in users
        ])

        period = 12
        periods = get_periods(period)

        # -----create 12 matches (1 for each period)-----
        matches = Match.objects.bulk_create([
            Match(
                initiator=self.brand,
                target=brand,
                is_match=True,
                match_at=period_[1] - timedelta(days=15)  # upper bound of a period - 15 days
            )
            for brand, period_ in zip(brands, periods)
        ])

        # update like time to fit the period
        for match, period_ in zip(matches, periods):
            match.like_at = period_[1] - timedelta(days=16)  # upper bound of a period - 16 days

        Match.objects.bulk_update(matches, ['like_at'])

        # -----create 12 collabs-----
        collab_data = {
            "success_assessment": 10,
            "success_reason": "string",
            "to_improve": "string",
            "subs_received": 2147483647,
            "leads_received": 2147483647,
            "sales_growth": "string",
            "audience_reach": 2147483647,
            "bill_change": "string",
            "new_offers": True,
            "new_offers_comment": "string",
            "perception_change": True,
            "brand_compliance": 10,
            "platform_help": 5,
            "difficulties": True,
            "difficulties_comment": "string"
        }

        collabs = Collaboration.objects.bulk_create([
            Collaboration(**collab_data, reporter=self.brand, collab_with=match.target, match=match)
            for match in matches
        ])

        # update collab time to fit the period
        for collab, period_ in zip(collabs, periods):
            collab.created_at = period_[1] - timedelta(days=15)

        Collaboration.objects.bulk_update(collabs, ['created_at'])
        # ---------------------------

        # check number of queries
        with self.assertNumQueriesLessThan(5, verbose=True):
            response = self.auth_client.get(f'{self.url}?period={period}')

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # length of the data must be equal to the period
        self.assertEqual(len(response.data), period)

        for stat_result in response.data:
            self.assertEqual(stat_result['likes'], 1)
            self.assertEqual(stat_result['matches'], 1)
            self.assertEqual(stat_result['collabs'], 1)
