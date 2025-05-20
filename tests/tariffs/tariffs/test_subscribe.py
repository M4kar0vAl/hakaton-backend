from datetime import timedelta

from cities_light.models import City, Country
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category
from core.apps.payments.models import PromoCode, Subscription

User = get_user_model()


class TariffSubscribeTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email=f'user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

        country = Country.objects.create(name='Country', continent='EU')
        city = City.objects.create(name='City', country=country)

        brand_data = cls.brand_data = {
            'tg_nickname': '@asfhbnaf',
            'city': city,
            'name': 'brand1',
            'position': 'position',
            'category': Category.objects.get(id=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        cls.brand = Brand.objects.create(user=cls.user, **brand_data)

        now = timezone.now()
        cls.promocode = PromoCode.objects.create(code='test', discount=5, expires_at=now + timedelta(days=30))

        cls.url = reverse('tariffs-subscribe')

    def test_tariff_subscribe_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'tariff': 2})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tariff_subscribe_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email=f'user2@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.post(self.url, {'tariff': 2})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tariff_subscribe_with_active_unexpired_subscription_not_allowed(self):
        self.auth_client.post(self.url, {'tariff': 2})
        response = self.auth_client.post(self.url, {'tariff': 3})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tariff_subscribe(self):
        response = self.auth_client.post(self.url, {'tariff': 2})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.user.brand.subscriptions.count(), 1)

        subscription = self.user.brand.subscriptions.get(is_active=True)

        self.assertEqual(response.data['id'], subscription.id)
        self.assertIsNone(response.data['promocode'])

    def test_tariff_subscribe_with_promocode(self):
        response = self.auth_client.post(self.url, {'tariff': 2, 'promocode': self.promocode.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.user.brand.subscriptions.count(), 1)
        self.assertEqual(response.data['promocode'], self.promocode.id)

    def test_tariff_subscribe_with_expired_promocode(self):
        """
        Should be ok when creating with expired promo code, because promo code is checked before payment.
        After payment subscribe api is called with promo code that was used in payment.
        Promo code can expire between check for validity and calling subscribe api.
        That's why it shouldn't be validated in subscribe action.

        flow:
            apply promo -> check for validity -> return promo code if everything is ok -> create payment link -> pay ->
            call subscribe api (no need to check validity here, because user has already paid) -> return subscription
        """
        expired_promocode = PromoCode.objects.create(
            code='expired_test', discount=5, expires_at=timezone.now() - timedelta(minutes=1)
        )

        response = self.auth_client.post(self.url, {'tariff': 2, 'promocode': expired_promocode.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.user.brand.subscriptions.count(), 1)
        self.assertEqual(response.data['promocode'], expired_promocode.id)

    def test_tariff_subscribe_trial_ignores_promocode(self):
        response = self.auth_client.post(self.url, {'tariff': 1, 'promocode': self.promocode.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.user.brand.subscriptions.count(), 1)
        self.assertIsNone(response.data['promocode'])

    def test_tariff_subscribe_deactivates_active_tariffs(self):
        initial_response = self.auth_client.post(self.url, {'tariff': 2})  # subscribe to the second tariff

        # manually expire subscription
        Subscription.objects.filter(id=initial_response.data['id']).update(
            end_date=timezone.now() - timedelta(minutes=1)
        )

        response = self.auth_client.post(self.url, {'tariff': 3})  # subscribe to the third tariff

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.brand.subscriptions.filter(is_active=True).count(), 1)
        self.assertEqual(self.brand.subscriptions.get(is_active=True).tariff.id, 3)
