from datetime import timedelta

from cities_light.models import City, Country
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category
from core.apps.payments.models import Tariff, PromoCode, Subscription

User = get_user_model()


class TariffsTestCase(APITestCase):
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

        cls.url = reverse('tariffs-list')

    def test_tariffs_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tarrifs(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), Tariff.objects.count())


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


class TariffUpgradeTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # bulk create 3 users
        users = User.objects.bulk_create([
            User(
                email=f'user{i}@example.com',
                phone='+79993332211',
                fullname='Юзеров Юзер Юзерович',
                password='Pass!234',
                is_active=True
            ) for i in range(1, 4)
        ])

        for i, user in enumerate(users, start=1):
            # set users to class attributes named user{i}
            setattr(cls, f'user{i}', user)

            # create APIClient instance for each user
            setattr(cls, f'auth_client{i}', APIClient())

            # force authenticate clients
            getattr(cls, f'auth_client{i}').force_authenticate(user)

        country = Country.objects.create(name='Country', continent='EU')
        city = City.objects.create(name='City', country=country)

        cls.brand_data = {
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

        cls.trial_brand = Brand.objects.create(user=cls.user1, **cls.brand_data)
        cls.lite_brand = Brand.objects.create(user=cls.user2, **cls.brand_data)
        cls.business_brand = Brand.objects.create(user=cls.user3, **cls.brand_data)

        tariffs = list(Tariff.objects.order_by('id'))
        cls.trial = tariffs[0]
        cls.lite = tariffs[1]
        cls.business = tariffs[2]

        now = timezone.now()

        cls.promocode = PromoCode.objects.create(code='test', discount=5, expires_at=now + timedelta(days=30))

        # create trial sub for auth_client1
        Subscription.objects.create(
            brand=cls.trial_brand,
            tariff=cls.trial,
            start_date=now,
            end_date=now + cls.trial.duration,
            is_active=True
        )

        # create lite  sub for auth_client2
        Subscription.objects.create(
            brand=cls.lite_brand,
            tariff=cls.lite,
            start_date=now,
            end_date=now + relativedelta(months=cls.lite.duration.days // 30),
            is_active=True
        )

        # create business sub for auth_client3
        Subscription.objects.create(
            brand=cls.business_brand,
            tariff=cls.business,
            start_date=now,
            end_date=now + relativedelta(months=cls.business.duration.days // 30),
            is_active=True
        )

        cls.url = reverse('tariffs-upgrade')

    def test_tariff_upgrade_unauthenticated_not_allowed(self):
        response = self.client.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tariff_upgrade_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email=f'user_wo_brand@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tariff_upgrade_wo_active_unexpired_sub_not_allowed(self):
        user = User.objects.create_user(
            email=f'user@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_sub = APIClient()
        auth_client_wo_sub.force_authenticate(user)

        Brand.objects.create(user=user, **self.brand_data)

        response = auth_client_wo_sub.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tariff_upgrade_for_brand_on_trial_not_allowed(self):
        response = self.auth_client1.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tariff_upgrade_for_brand_on_business_not_allowed(self):
        response = self.auth_client3.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tariff_upgrade(self):
        response = self.auth_client2.patch(self.url, {'tariff': self.business.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that another subscription wasn't created
        self.assertEqual(self.lite_brand.subscriptions.count(), 1)

        current_sub = self.lite_brand.subscriptions.get()

        self.assertEqual(current_sub.tariff_id, self.business.id)  # check that upgraded to business
        self.assertEqual(current_sub.upgraded_from_id, self.lite.id)  # check that upgraded from lite
        self.assertIsNotNone(current_sub.upgraded_at)  # check that upgraded timestamp is not None

    def test_tariff_upgrade_cannot_upgrade_to_trial(self):
        response = self.auth_client2.patch(self.url, {'tariff': self.trial.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tariff_upgrade_cannot_upgrade_to_lite(self):
        response = self.auth_client2.patch(self.url, {'tariff': self.lite.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
