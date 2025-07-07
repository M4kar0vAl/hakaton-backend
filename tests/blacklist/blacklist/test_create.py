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

        cls.url = reverse('blacklist-list')

    def test_blacklist_create_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'blocked': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blacklist_create_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        client_wo_brand = APIClientFactory(user=user_wo_brand)

        response = client_wo_brand.post(self.url, {'blocked': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blacklist_create_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClientFactory(user=user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.post(self.url, {'blocked': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blacklist_create(self):
        response = self.auth_client1.post(self.url, {'blocked': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        try:
            bl = BlackList.objects.get(id=response.data['id'])
        except BlackList.DoesNotExist:
            bl = None

        self.assertIsNotNone(bl)
        self.assertEqual(bl.initiator_id, self.brand1.id)
        self.assertEqual(bl.blocked_id, self.brand2.id)

    def test_blacklist_create_already_blocked(self):
        BlackListFactory(initiator=self.brand1, blocked=self.brand2)  # brand 1 blocks brand2

        # brand1 tries to block brand2 again
        response = self.auth_client1.post(self.url, {'blocked': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # check that second row wasn't created in db
        self.assertEqual(self.brand1.blacklist_as_initiator.count(), 1)

    def test_blacklist_create_cannot_block_yourself(self):
        response = self.auth_client1.post(self.url, {'blocked': self.brand1.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # check that blacklist entity wasn't created in db
        self.assertEqual(self.brand1.blacklist_as_initiator.count(), 0)
