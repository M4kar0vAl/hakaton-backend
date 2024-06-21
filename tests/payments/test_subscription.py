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
            published=True,
            subscription=None,
            sub_expire=None,
            tg_nickname='@telegram',
            phone='+79998884422',
            brand_name_pos='text',
            inst_brand_url='text text',
            brand_site_url='text text',
            topics='темы',
            mission_statement='text',
            target_audience='text',
            unique_product_is='text',
            product_description='text text',
            problem_solving='text text',
            business_group='text text',
            logo='Лого',
            photo='Фото представителя',
            product_photo='Фото продукта',
            fullname='text',
            email='email@example.com',
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
