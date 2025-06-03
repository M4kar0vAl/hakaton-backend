from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.models import BlackList
from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.models import Tariff, Subscription


class BrandRetrieveTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2 = UserFactory.create_batch(2)
        cls.auth_client1, cls.auth_client2 = APIClient(), APIClient()
        cls.auth_client1.force_authenticate(cls.user1)
        cls.auth_client2.force_authenticate(cls.user2)

        cls.brand1 = BrandShortFactory(user=cls.user1)
        cls.brand2 = BrandShortFactory(user=cls.user2)

        cls.tariff = Tariff.objects.get(name='Lite Match')
        cls.tariff_relativedelta = cls.tariff.get_duration_as_relativedelta()
        now = timezone.now()

        Subscription.objects.create(
            brand=cls.brand1,
            tariff=cls.tariff,
            start_date=now,
            end_date=now + cls.tariff_relativedelta,
            is_active=True
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
        BlackList.objects.create(initiator=self.brand2, blocked=self.brand1)  # brand2 blocked brand1

        response = self.auth_client1.get(self.brand2_url)  # brand1 tries to get info about brand2

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_brand_retrieve_if_blocked_target(self):
        BlackList.objects.create(initiator=self.brand1, blocked=self.brand2)  # brand1 blocked brand2

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
