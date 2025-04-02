from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.analytics.models import BrandActivity
from core.apps.brand.models import Category, Brand

User = get_user_model()


class LogPaymentTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

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

        cls.brand = Brand.objects.create(user=cls.user, **cls.brand_data)

        cls.url = reverse('analytics-log_payment')

    def test_log_payment_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_log_payment_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user_wo_brand@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_brand = APIClient()
        client_wo_brand.force_authenticate(user_wo_brand)

        response = client_wo_brand.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_log_payment(self):
        response = self.auth_client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check that instance was created in db
        self.assertTrue(BrandActivity.objects.filter(id=response.data['id']).exists())
