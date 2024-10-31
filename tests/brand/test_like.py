from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Category, Brand, Match
from core.apps.chat.models import Room

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

        brand_data = {
            'tg_nickname': '@asfhbnaf',
            'name': 'brand1',
            'position': 'position',
            'category': Category.objects.get(pk=1),
            'inst_url': 'https://example.com',
            'vk_url': 'https://example.com',
            'tg_url': 'https://example.com',
            'wb_url': 'https://example.com',
            'lamoda_url': 'https://example.com',
            'site_url': 'https://example.com',
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        cls.brand1 = Brand.objects.create(user=cls.user1, **brand_data)
        cls.brand2 = Brand.objects.create(user=cls.user2, **brand_data)

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

        self.assertTrue(Match.objects.filter(is_match=True).exists())  # check that match exists

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
