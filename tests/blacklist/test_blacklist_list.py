from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.blacklist.models import BlackList
from core.apps.brand.models import Brand, Category
from core.apps.payments.models import Tariff, Subscription
from tests.mixins import AssertNumQueriesLessThanMixin

User = get_user_model()


class BlacklistListTestCase(
    APITestCase,
    AssertNumQueriesLessThanMixin,
):
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

        cls.url = reverse('blacklist-list')

    def test_blacklist_list_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blacklist_list_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user_wo_brand@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_brand = APIClient()
        client_wo_brand.force_authenticate(user_wo_brand)

        response = client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blacklist_list_wo_active_sub_not_allowed(self):
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

        response = client_wo_active_sub.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blacklist_list(self):
        another_user = User.objects.create_user(
            email='another_user@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        another_brand = Brand.objects.create(user=another_user, **self.brand_data)

        bl1 = BlackList.objects.create(initiator=self.brand1, blocked=self.brand2)
        bl2 = BlackList.objects.create(initiator=self.brand1, blocked=another_brand)

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
        bl1, bl2 = BlackList.objects.bulk_create([
            BlackList(initiator=self.brand1, blocked=self.brand2),
            BlackList(initiator=self.brand2, blocked=self.brand1)
        ])

        response = self.auth_client1.get(self.url)

        results = response.data['results']

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], bl1.id)

    def test_blacklist_list_number_of_queries(self):
        users = User.objects.bulk_create([
            User(
                email=f'user_{i}@example.com',
                phone='+79993332211',
                fullname='Юзеров Юзер Юзерович',
                password='Pass!234',
                is_active=True
            )
            for i in range(50)
        ])

        brands = Brand.objects.bulk_create([
            Brand(user=user, **self.brand_data)
            for user in users
        ])

        blacklist_entities = BlackList.objects.bulk_create([
            BlackList(initiator=self.brand1, blocked=brand)
            for brand in brands
        ])

        with self.assertNumQueriesLessThan(3, verbose=True):
            response = self.auth_client1.get(self.url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.assertEqual(len(response.data['results']), len(blacklist_entities))
