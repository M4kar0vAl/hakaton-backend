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

        cls.url = reverse('blacklist-list')

    def test_blacklist_create_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'blocked': self.brand2.id})

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

        response = client_wo_brand.post(self.url, {'blocked': self.brand2.id})

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
        BlackList.objects.create(initiator=self.brand1, blocked=self.brand2)  # brand 1 blocks brand2

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
