import factory
from django.test import tag
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory, MatchFactory
from core.apps.brand.models import Brand
from core.apps.payments.factories import SubscriptionFactory
from tests.mixins import AssertNumQueriesLessThanMixin


class BrandMyMatchesTestCase(
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
            3, user=factory.Iterator([cls.user1, cls.user2, cls.user3])
        )

        SubscriptionFactory.create_batch(3, brand=factory.Iterator([cls.brand1, cls.brand2, cls.brand3]))

        cls.url = reverse('brand-my_matches')

    def create_n_matches(self, n: int) -> Brand:
        """
        Create n matches in db.

        Will be created:
         - n + 1 users
         - n + 1 brands

        Returns:
            Brand instance that have n matches associated with it
        """
        users = UserFactory.create_batch(n + 1)
        brands = BrandShortFactory.create_batch(n + 1, user=factory.Iterator(users))
        brand_with_matches = brands.pop()

        MatchFactory.create_batch(n, initiator=brand_with_matches, target=factory.Iterator(brands))

        return brand_with_matches

    def test_my_matches_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_matches_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_matches_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_matches_no_matches(self):
        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that returned list is empty
        self.assertFalse(response.data['results'])

    def test_my_matches(self):
        match = MatchFactory(initiator=self.brand1, target=self.brand2)  # brand1 has match with brand2

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
        self.assertEqual(client1_response.data['results'][0]['match_room'], match.room.pk)
        self.assertEqual(client2_response.data['results'][0]['match_room'], match.room.pk)

    def test_my_matches_can_return_more_than_one_brand(self):
        # brand1 has match with brand2 and brand3
        MatchFactory.create_batch(2, initiator=self.brand1, target=factory.Iterator([self.brand2, self.brand3]))

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_my_matches_returns_matches_of_current_brand(self):
        MatchFactory(initiator=self.brand1, target=self.brand2)  # brand1 has match with brand2
        MatchFactory(initiator=self.brand2, target=self.brand3)  # brand2 has match with brand3

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_my_matches_excludes_likes(self):
        MatchFactory(initiator=self.brand1, target=self.brand2)  # brand1 has match with brand2
        MatchFactory(like=True, initiator=self.brand1, target=self.brand3)  # brand1 likes brand3

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    @tag('slow')
    def test_my_matches_number_of_queries(self):
        brand = self.create_n_matches(50)
        client = APIClient()
        client.force_authenticate(brand.user)

        SubscriptionFactory(brand=brand)

        with self.assertNumQueriesLessThan(6, verbose=True):
            response = client.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_my_matches_ordering(self):
        # brand1 has match with brand2 and brand3
        MatchFactory.create_batch(2, initiator=self.brand1, target=factory.Iterator([self.brand2, self.brand3]))

        response = self.auth_client1.get(self.url)
        results = response.data['results']

        self.assertEqual(results[0]['id'], self.brand3.id)
        self.assertEqual(results[1]['id'], self.brand2.id)
