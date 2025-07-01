import factory
from django.test import tag
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.factories import BlackListFactory
from core.apps.brand.factories import BrandShortFactory, MatchFactory
from core.apps.brand.models import Brand
from core.apps.payments.factories import SubscriptionFactory
from tests.factories import APIClientFactory
from tests.mixins import AssertNumQueriesLessThanMixin


class BrandMyLikesTestCase(
    APITestCase,
    AssertNumQueriesLessThanMixin
):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2, cls.user3 = UserFactory.create_batch(3)
        cls.auth_client1, cls.auth_client2, cls.auth_client3 = APIClientFactory.create_batch(
            3, user=factory.Iterator([cls.user1, cls.user2, cls.user3])
        )

        cls.brand1, cls.brand2, cls.brand3 = BrandShortFactory.create_batch(
            3,
            user=factory.Iterator([cls.user1, cls.user2, cls.user3]),
            has_sub=factory.Iterator([True, True, False])
        )

        cls.url = reverse('brand-my_likes')

    def create_n_likes(self, n: int) -> Brand:
        """
            Create n likes in db.

            Will be created:
             - n + 1 users
             - n + 1 brands

            Returns:
                Brand instance that have n likes associated with it
        """

        users = UserFactory.create_batch(n + 1)
        brands = BrandShortFactory.create_batch(n + 1, user=factory.Iterator(users))
        brand_with_likes = brands.pop()

        MatchFactory.create_batch(n, like=True, initiator=brand_with_likes, target=factory.Iterator(brands))

        return brand_with_likes

    def test_my_likes_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_likes_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClientFactory(user=user_wo_brand)

        response = auth_client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_likes_wo_active_sub_not_allowed(self):
        response = self.auth_client3.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_likes_no_likes(self):
        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that returned list is empty
        self.assertFalse(response.data['results'])

    def test_my_likes_no_instant_coops(self):
        MatchFactory(like=True, initiator=self.brand1, target=self.brand2)  # brand1 likes brand2
        response = self.auth_client1.get(self.url)  # get brands that were liked by brand1

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that there is only one brand that was liked by brand1
        self.assertEqual(len(response.data['results']), 1)

        # check that there is no instant room for these brands
        self.assertIsNone(response.data['results'][0]['instant_room'])

    def test_my_likes_with_instant_coop(self):
        # brand1 instant coops brand2, INSTANT room is created
        instant_coop = MatchFactory(instant_coop=True, initiator=self.brand1, target=self.brand2)

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that instant room is not None
        self.assertIsNotNone(response.data['results'][0]['instant_room'])
        self.assertEqual(response.data['results'][0]['instant_room'], instant_coop.room_id)

    def test_my_likes_includes_only_likes_of_current_brand(self):
        MatchFactory(like=True, initiator=self.brand1, target=self.brand2)  # brand1 likes brand2
        MatchFactory(like=True, initiator=self.brand2, target=self.brand1)  # brand2 likes brand1

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that there is only 1 liked brand
        self.assertEqual(len(response.data['results']), 1)

    def test_my_likes_exclude_matches(self):
        MatchFactory(initiator=self.brand1, target=self.brand2)  # brand1 has match with brand2

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that response is empty
        self.assertFalse(response.data['results'])

    def test_my_likes_exclude_blacklist(self):
        # brand1 likes brand2 and brand3
        MatchFactory.create_batch(
            2, like=True, initiator=self.brand1, target=factory.Iterator([self.brand2, self.brand3])
        )

        BlackListFactory(initiator=self.brand1, blocked=self.brand2)  # brand1 blocks brand2
        BlackListFactory(initiator=self.brand3, blocked=self.brand1)  # brand3 blocks brand1

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        # results must exclude both blocked brands and brands that blocked the current one
        self.assertEqual(len(results), 0)

    def test_my_likes_can_return_more_than_one_brand(self):
        MatchFactory(instant_coop=True, initiator=self.brand1, target=self.brand2)  # brand 1 instant coops brand2
        MatchFactory(like=True, initiator=self.brand1, target=self.brand3)  # brand1 likes brand3

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 2)

    @tag('slow')
    def test_my_likes_number_of_queries(self):
        brand = self.create_n_likes(50)
        client = APIClientFactory(user=brand.user)

        SubscriptionFactory(brand=brand)

        with self.assertNumQueriesLessThan(6, verbose=True):
            response = client.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_my_likes_ordering(self):
        # brand1 likes brand2 and brand1 likes brand3
        MatchFactory.create_batch(
            2, like=True, initiator=self.brand1, target=factory.Iterator([self.brand2, self.brand3])
        )

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        self.assertEqual(results[0]['id'], self.brand3.id)
        self.assertEqual(results[1]['id'], self.brand2.id)
