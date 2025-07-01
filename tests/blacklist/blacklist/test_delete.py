import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.factories import BlackListFactory
from core.apps.blacklist.models import BlackList
from core.apps.brand.factories import BrandShortFactory
from tests.factories import APIClientFactory


class BlacklistCreateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2 = UserFactory.create_batch(2)
        cls.auth_client1, cls.auth_client2 = APIClientFactory.create_batch(
            2, user=factory.Iterator([cls.user1, cls.user2])
        )

        cls.brand1, cls.brand2 = BrandShortFactory.create_batch(
            2, user=factory.Iterator([cls.user1, cls.user2]), has_sub=True
        )

        cls.blacklist = BlackListFactory(initiator=cls.brand1, blocked=cls.brand2)

        cls.url = reverse('blacklist-detail', kwargs={'pk': cls.blacklist.pk})

    def test_blacklist_create_unauthenticated_not_allowed(self):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blacklist_create_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        client_wo_brand = APIClientFactory(user=user_wo_brand)

        response = client_wo_brand.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blacklist_create_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClientFactory(user=user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blacklist_delete_if_not_initiator_not_allowed(self):
        response = self.auth_client2.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # check that existing instance wasn't deleted
        self.assertTrue(BlackList.objects.filter(id=self.blacklist.id).exists())

    def test_blacklist_delete(self):
        response = self.auth_client1.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(response.data)
        self.assertFalse(BlackList.objects.filter(id=self.blacklist.id).exists())
