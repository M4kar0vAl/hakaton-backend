import factory
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.models import BlackList
from core.apps.brand.factories import BrandShortFactory, LikeFactory, MatchFactory
from core.apps.payments.models import Tariff, Subscription
from tests.mixins import AssertNumQueriesLessThanMixin


class LikedByTestCase(
    APITestCase,
    AssertNumQueriesLessThanMixin
):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2, cls.user3 = UserFactory.create_batch(3)
        cls.auth_client1, cls.auth_client2, cls.auth_client3 = APIClient(), APIClient(), APIClient()
        cls.auth_client1.force_authenticate(cls.user1)
        cls.auth_client2.force_authenticate(cls.user2)
        cls.auth_client3.force_authenticate(cls.user3)

        cls.brand1 = BrandShortFactory(user=cls.user1)
        cls.brand2 = BrandShortFactory(user=cls.user2)
        cls.brand3 = BrandShortFactory(user=cls.user3)

        cls.tariff = Tariff.objects.get(name='Business Match')
        cls.tariff_relativedelta = cls.tariff.get_duration_as_relativedelta()
        now = timezone.now()

        Subscription.objects.create(
            brand=cls.brand1,
            tariff=cls.tariff,
            start_date=now,
            end_date=now + cls.tariff_relativedelta,
            is_active=True
        )

        Subscription.objects.create(
            brand=cls.brand2,
            tariff=cls.tariff,
            start_date=now,
            end_date=now + cls.tariff_relativedelta,
            is_active=True
        )

        Subscription.objects.create(
            brand=cls.brand3,
            tariff=cls.tariff,
            start_date=now,
            end_date=now + cls.tariff_relativedelta,
            is_active=True
        )

        cls.url = reverse('brand-liked_by')

    def test_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_without_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client = APIClient()
        auth_client.force_authenticate(user_wo_brand)

        response = auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_liked_by_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_liked_by_returns_empty_list_if_no_likes(self):
        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['results'])

    def test_liked_by_returns_correct_list_of_brands(self):
        # brand2 likes brand1 and brand3
        LikeFactory.create_batch(2, initiator=self.brand2, target=factory.Iterator([self.brand1, self.brand3]))
        LikeFactory(initiator=self.brand1, target=self.brand3)  # brand1 likes brand3

        response = self.auth_client1.get(self.url)  # get who liked brand1

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.brand2.id)

    def test_liked_by_excludes_matches(self):
        LikeFactory(initiator=self.brand2, target=self.brand1)  # brand2 likes brand1
        MatchFactory(initiator=self.brand3, target=self.brand1)  # brand3 has match with brand1

        response = self.auth_client1.get(self.url)  # get who liked brand1

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 1)

    def test_liked_by_excludes_blacklist(self):
        LikeFactory(initiator=self.brand2, target=self.brand1)  # brand2 likes brand1
        LikeFactory(initiator=self.brand3, target=self.brand1)  # brand3 likes brand1

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
        LikeFactory(initiator=self.brand2, target=self.brand1)  # brand2 likes brand1
        LikeFactory(initiator=self.brand3, target=self.brand1)  # brand3 likes brand1

        with self.assertNumQueriesLessThan(3, verbose=True):
            response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_liked_by_ordering(self):
        LikeFactory(initiator=self.brand2, target=self.brand1)  # brand2 likes brand1
        LikeFactory(initiator=self.brand3, target=self.brand1)  # brand3 likes brand1

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        # results are ordered by the time of a like descending
        self.assertEqual(results[0]['id'], self.brand3.id)
        self.assertEqual(results[1]['id'], self.brand2.id)
