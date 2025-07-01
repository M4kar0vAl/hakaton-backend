import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.factories import BlackListFactory
from core.apps.brand.factories import BrandShortFactory
from tests.factories import APIClientFactory
from tests.mixins import AssertNumQueriesLessThanMixin


class BlacklistListTestCase(
    APITestCase,
    AssertNumQueriesLessThanMixin,
):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2 = UserFactory.create_batch(2)
        cls.auth_client1, cls.auth_client2 = APIClientFactory.create_batch(
            2, user=factory.Iterator([cls.user1, cls.user2])
        )

        cls.brand1, cls.brand2 = BrandShortFactory.create_batch(
            2, user=factory.Iterator([cls.user1, cls.user2]), has_sub=True
        )

        cls.url = reverse('blacklist-list')

    def test_blacklist_list_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blacklist_list_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        client_wo_brand = APIClientFactory(user=user_wo_brand)

        response = client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blacklist_list_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClientFactory(user=user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blacklist_list(self):
        another_brand = BrandShortFactory()

        bl1, bl2 = BlackListFactory.create_batch(
            2, initiator=self.brand1, blocked=factory.Iterator([self.brand2, another_brand])
        )

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        self.assertEqual(len(results), 2)
        # check ordering
        self.assertEqual(results[0]['id'], bl2.id)
        self.assertEqual(results[1]['id'], bl1.id)

        self.assertEqual(results[0]['blocked']['id'], another_brand.id)
        self.assertEqual(results[1]['blocked']['id'], self.brand2.id)

    def test_blacklist_list_excludes_entities_where_current_brand_is_blocked(self):
        # brand1 and brand2 blocked each other
        bl1, bl2 = BlackListFactory.create_batch(
            2,
            initiator=factory.Iterator([self.brand1, self.brand2]),
            blocked=factory.Iterator([self.brand2, self.brand1])
        )

        response = self.auth_client1.get(self.url)
        results = response.data['results']

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], bl1.id)

    def test_blacklist_list_number_of_queries(self):
        blacklist_entities = BlackListFactory.create_batch(50, initiator=self.brand1)

        with self.assertNumQueriesLessThan(3, verbose=True):
            response = self.auth_client1.get(self.url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), len(blacklist_entities))
