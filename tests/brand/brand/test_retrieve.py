import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.factories import BlackListFactory
from core.apps.brand.factories import BrandShortFactory


class BrandRetrieveTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2 = UserFactory.create_batch(2)
        cls.auth_client1, cls.auth_client2 = APIClient(), APIClient()
        cls.auth_client1.force_authenticate(cls.user1)
        cls.auth_client2.force_authenticate(cls.user2)
        cls.brand1, cls.brand2 = BrandShortFactory.create_batch(
            2, user=factory.Iterator([cls.user1, cls.user2]), has_sub=factory.Iterator([True, False])
        )

        cls.brand1_url = reverse('brand-detail', kwargs={'pk': cls.brand1.pk})
        cls.brand2_url = reverse('brand-detail', kwargs={'pk': cls.brand2.pk})

    def test_brand_retrieve_unauthenticated_not_allowed(self):
        response = self.client.get(self.brand1_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_brand_retrieve_wo_brand(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.get(self.brand1_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_brand_retrieve_wo_active_sub_not_allowed(self):
        response = self.auth_client2.get(self.brand1_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_brand_retrieve_if_in_blacklist_of_target_not_allowed(self):
        BlackListFactory(initiator=self.brand2, blocked=self.brand1)  # brand2 blocked brand1

        response = self.auth_client1.get(self.brand2_url)  # brand1 tries to get info about brand2

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_brand_retrieve_if_blocked_target(self):
        BlackListFactory(initiator=self.brand1, blocked=self.brand2)  # brand1 blocked brand2

        response = self.auth_client1.get(self.brand2_url)  # brand1 tries to get nfo about brand2

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.brand2.id)

    def test_brand_retrieve_other_brand(self):
        response = self.auth_client1.get(self.brand2_url)  # brand1 gets info about brand2

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.brand2.id)

    def test_brand_retrieve_self(self):
        response = self.auth_client1.get(self.brand1_url)  # brand1 gets info about brand1

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
