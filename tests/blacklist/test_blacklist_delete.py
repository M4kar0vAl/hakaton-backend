from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.blacklist.models import BlackList
from core.apps.brand.models import Category, Brand
from core.apps.payments.models import Tariff, Subscription

User = get_user_model()


class BlacklistCreateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.user2 = User.objects.create_user(
            email='user2@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.auth_client1 = APIClient()
        cls.auth_client2 = APIClient()
        cls.auth_client1.force_authenticate(cls.user1)
        cls.auth_client2.force_authenticate(cls.user2)

        cls.brand_data = {
            'tg_nickname': '@asfhbnaf',
            'name': 'brand1',
            'position': 'position',
            'category': Category.objects.get(pk=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        brands = Brand.objects.bulk_create([
            Brand(user=user, **cls.brand_data)
            for user in [cls.user1, cls.user2]
        ])

        cls.brand1, cls.brand2 = brands

        cls.tariff = Tariff.objects.get(name='Business Match')
        now = timezone.now()

        Subscription.objects.bulk_create([
            Subscription(
                brand=brand,
                tariff=cls.tariff,
                start_date=now,
                end_date=now + relativedelta(months=cls.tariff.duration.days // 30),
                is_active=True
            )
            for brand in brands
        ])

        cls.blacklist = BlackList.objects.create(initiator=cls.brand1, blocked=cls.brand2)

        cls.url = reverse('blacklist-detail', kwargs={'pk': cls.blacklist.pk})

    def test_blacklist_create_unauthenticated_not_allowed(self):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blacklist_create_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user_wo_brand@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_brand = APIClient()
        client_wo_brand.force_authenticate(user_wo_brand)

        response = client_wo_brand.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blacklist_create_wo_active_sub_not_allowed(self):
        user_wo_active_sub = User.objects.create_user(
            email='user_wo_active_sub@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        Brand.objects.create(user=user_wo_active_sub, **self.brand_data)

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
