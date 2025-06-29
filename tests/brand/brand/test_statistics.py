from datetime import timedelta

import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory, MatchFactory, CollaborationFactory
from core.apps.brand.utils import get_periods
from tests.mixins import AssertNumQueriesLessThanMixin


class StatisticsTestCase(
    APITestCase,
    AssertNumQueriesLessThanMixin
):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)
        cls.brand = BrandShortFactory(user=cls.user, has_sub=True)

        cls.url = reverse('brand-statistics')

    def test_statistics_unauthenticated_not_allowed(self):
        response = self.client.get(f'{self.url}?period=1')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_statistics_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        client_wo_brand = APIClient()
        client_wo_brand.force_authenticate(user_wo_brand)

        response = client_wo_brand.get(f'{self.url}?period=1')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_statistics_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.get(f'{self.url}?period=1')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_statistics(self):
        brand1, brand2, brand3 = BrandShortFactory.create_batch(3)

        # initial brand has matches with brand1 and brand2 (and he is an initiator of both) => 2 likes and 2 matches
        match1, match2 = MatchFactory.create_batch(2, initiator=self.brand, target=factory.Iterator([brand1, brand2]))
        MatchFactory(like=True, initiator=self.brand, target=brand3)  # initial brand likes brand3 => 1 like

        # initial brand reports about collab with brand1 => 1 collab
        CollaborationFactory(reporter=self.brand, collab_with=brand1, match=match1)
        # brand2 reports about collab with initial brand => 1 collab
        CollaborationFactory(reporter=brand2, collab_with=self.brand, match=match2)

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
        period = 12
        periods = get_periods(period)

        # create 1 brand for each period
        brands = BrandShortFactory.create_batch(period)

        # create 1 match for each period
        MatchFactory.create_batch(
            period,
            initiator=self.brand,
            target=factory.Iterator(brands),
            like_at=factory.Iterator(periods, getter=lambda p: p[1] - timedelta(days=16)),
            match_at=factory.Iterator(periods, getter=lambda p: p[1] - timedelta(days=15))
        )

        # create 1 collab for each period
        CollaborationFactory.create_batch(
            period,
            reporter=self.brand,
            collab_with=factory.Iterator(brands),
            created_at=factory.Iterator(periods, getter=lambda p: p[1] - timedelta(days=15))
        )

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
