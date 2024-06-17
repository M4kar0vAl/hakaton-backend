import datetime

from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand
from core.apps.payments.models import Subscription

User = get_user_model()


class BoardTestCase(APITestCase):
    def setUp(self):
        user_data = {
            'email': 'user1@example.com',
            'phone': '+79993332211',
            'password': 'Pass!234',
            'is_active': True,
        }
        self.user = User.objects.create_user(**user_data)
        self.client = APIClient()
        self.auth_client = APIClient()
        self.auth_client.force_authenticate(self.user)
        self.brand = Brand.objects.create(
            user=self.user,
            fi='User1 Test',
            birth_date=datetime.datetime.now(),
            tg_nickname='tatad1',
            brand_name_pos='manager SuperBrand',
            inst_brand_url='instagram link',
            inst_profile_url='instagram profile',
            tg_brand_url='telegram profile',
            brand_site_url='site link',
            topics='темы',
            subs_count='10k',
            avg_bill='10k',
            values='Ценности',
            target_audience='Целевая аудитория',
            territory='География бренда',
            logo='Лого',
            photo='Фото представителя',
            product_photo='Фото продукта',
        )

    def test_get_subs(self):
        response = self.client.get(reverse('payments-list'))
        self.assertEqual(200, response.status_code)
        self.assertEqual(3, len(response.json()))

    def test_set_sub_brand(self):
        subscribe = Subscription.objects.get(cost=12000)
        data = {
            'sub': subscribe.id,
        }
        response = self.auth_client.post(
            reverse('payments-subscription'),
            data=data,
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(subscribe, self.brand.subscription)
        self.assertEqual(
            (datetime.datetime.now() + datetime.timedelta(days=365)).date(),
            self.brand.sub_expire.date()
        )

    def test_perms_sub_brand(self):
        subscribe = Subscription.objects.get(cost=12000)
        data = {
            'sub': subscribe.id,
        }
        response = self.client.post(
            reverse('payments-subscription'),
            data=data,
        )
        self.assertEqual(401, response.status_code)

    def test_promocode(self):
        subscribe = Subscription.objects.get(cost=12000)
        data = {
            'sub': subscribe.id,
            'promocode': 'discount5'
        }
        response = self.auth_client.post(
            reverse('payments-subscription'),
            data=data,
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(12000 * 0.95, response.json()['cost'])
