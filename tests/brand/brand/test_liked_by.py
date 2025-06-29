import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.factories import BlackListFactory
from core.apps.brand.factories import BrandShortFactory, MatchFactory
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

        cls.brand1, cls.brand2, cls.brand3 = BrandShortFactory.create_batch(
            3, user=factory.Iterator([cls.user1, cls.user2, cls.user3]), has_sub=True
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
        MatchFactory.create_batch(
            2, like=True, initiator=self.brand2, target=factory.Iterator([self.brand1, self.brand3])
        )
        MatchFactory(like=True, initiator=self.brand1, target=self.brand3)  # brand1 likes brand3

        response = self.auth_client1.get(self.url)  # get who liked brand1

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.brand2.id)

    def test_liked_by_excludes_matches(self):
        MatchFactory(like=True, initiator=self.brand2, target=self.brand1)  # brand2 likes brand1
        MatchFactory(initiator=self.brand3, target=self.brand1)  # brand3 has match with brand1

        response = self.auth_client1.get(self.url)  # get who liked brand1

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 1)

    def test_liked_by_excludes_blacklist(self):
        # brand2 likes brand1 and brand3 likes brand1
        MatchFactory.create_batch(
            2, like=True, initiator=factory.Iterator([self.brand2, self.brand3]), target=self.brand1
        )

        BlackListFactory(initiator=self.brand2, blocked=self.brand1)  # brand2 blocks brand1
        BlackListFactory(initiator=self.brand1, blocked=self.brand3)  # brand1 blocks brand3

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        # results must exclude both blocked brands and brands that blocked the current one
        self.assertEqual(len(results), 0)

    def test_liked_by_number_of_queries(self):
        # brand2 likes brand1 and brand3 likes brand1
        MatchFactory.create_batch(
            2, like=True, initiator=factory.Iterator([self.brand2, self.brand3]), target=self.brand1
        )

        with self.assertNumQueriesLessThan(3, verbose=True):
            response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_liked_by_ordering(self):
        # brand2 likes brand1 and brand3 likes brand1
        MatchFactory.create_batch(
            2, like=True, initiator=factory.Iterator([self.brand2, self.brand3]), target=self.brand1
        )

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        # results are ordered by the time of a like descending
        self.assertEqual(results[0]['id'], self.brand3.id)
        self.assertEqual(results[1]['id'], self.brand2.id)
