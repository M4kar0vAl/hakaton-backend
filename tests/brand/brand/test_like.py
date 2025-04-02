from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.blacklist.models import BlackList
from core.apps.brand.models import Category, Brand, Match
from core.apps.chat.models import Room
from core.apps.payments.models import Subscription, Tariff

User = get_user_model()


class BrandLikeTestCase(APITestCase):
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
            phone='+79993332212',
            fullname='Юзеров Юзер1 Юзерович',
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

        cls.brand1 = Brand.objects.create(user=cls.user1, **cls.brand_data)
        cls.brand2 = Brand.objects.create(user=cls.user2, **cls.brand_data)

        cls.tariff = Tariff.objects.get(name='Business Match')
        cls.tariff_relativedelta = cls.tariff.get_duration_as_relativedelta()
        now = timezone.now()

        Subscription.objects.create(
            brand=cls.brand1,
            tariff=cls.tariff,
            start_date=now,
            end_date=now + cls.tariff_relativedelta,
            is_active=True
        )

        Subscription.objects.create(
            brand=cls.brand2,
            tariff=cls.tariff,
            start_date=now,
            end_date=now + cls.tariff_relativedelta,
            is_active=True
        )

        cls.url = reverse('brand-like')

    def test_like_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_like_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user3@example.com',
            phone='+79993332213',
            fullname='Юзеров Юзер2 Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_like_wo_active_sub_not_allowed(self):
        user_wo_active_sub = User.objects.create_user(
            email='user3@example.com',
            phone='+79993332213',
            fullname='Юзеров Юзер2 Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        Brand.objects.create(user=user_wo_active_sub, **self.brand_data)

        response = client_wo_active_sub.post(self.url, {'target': self.brand1.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_like_if_in_blacklist_of_target_not_allowed(self):
        BlackList.objects.create(initiator=self.brand2, blocked=self.brand1)  # brand2 blocked brand1

        response = self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 tries to like brand2

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_like_if_blocked_target_not_allowed(self):
        BlackList.objects.create(initiator=self.brand1, blocked=self.brand2)  # brand1 blocked brand2

        response = self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 tries to like brand2

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_like_yourself_not_allowed(self):
        response = self.auth_client1.post(self.url, {'target': self.brand1.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_like(self):
        response = self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 likes brand2

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Match.objects.filter(initiator=self.brand1, target=self.brand2, is_match=False).exists())

    def test_cannot_like_twice_same_brand(self):
        self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 likes brand2
        response = self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 likes brand2 AGAIN

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_like_each_other_leads_to_match(self):
        self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 likes brand2
        response = self.auth_client2.post(self.url, {'target': self.brand1.id})  # brand2 likes brand1 MATCH

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Match.objects.filter(id=response.data['id'], is_match=True).exists())  # check that match exists

        match = Match.objects.get(id=response.data['id'])

        # check that match time was set
        self.assertIsNotNone(match.match_at)

        # check that match doesn't create another instance in db and only updates the old one
        self.assertEqual(Match.objects.count(), 1)

        # check that room was created
        self.assertEqual(Room.objects.count(), 1)

        room = Room.objects.prefetch_related('participants').get(pk=response.data['room'])

        # check that room type is MATCH
        self.assertEqual(room.type, Room.MATCH)

        # check that users were added to room participants
        self.assertTrue(self.brand1.user in room.participants.all())
        self.assertTrue(self.brand2.user in room.participants.all())

    def test_cannot_like_after_match(self):
        self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 likes brand2
        self.auth_client2.post(self.url, {'target': self.brand1.id})  # brand2 likes brand1 MATCH

        response = self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 likes brand2 AGAIN

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Match.objects.count(), 1)

    def test_like_not_existing_brand(self):
        response = self.auth_client1.post(self.url, {'target': 0})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_like_in_response_if_instant_cooped(self):
        self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 likes brand2

        # brand1 instant coop brand2
        instant_coop_response = self.auth_client1.post(reverse('brand-instant-coop'), {'target': self.brand2.id})

        response = self.auth_client2.post(self.url, {'target': self.brand1.id})  # brand2 likes brand1 MATCH

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        instant_room_id = instant_coop_response.data['id']
        room_id = response.data['room']

        # check that id of the room did not change
        self.assertEqual(room_id, instant_room_id)

        # check that room type was changed to MATCH
        room = Room.objects.get(id=room_id)
        self.assertEqual(room.type, Room.MATCH)
