from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.analytics.models import MatchActivity
from core.apps.brand.models import Brand, Category, Collaboration

User = get_user_model()


class CollaborationTestCase(APITestCase):
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

        cls.collaboration_data = {
            "success_assessment": 10,
            "success_reason": "string",
            "to_improve": "string",
            "subs_received": 2147483647,
            "leads_received": 2147483647,
            "sales_growth": "string",
            "audience_reach": 2147483647,
            "bill_change": "string",
            "new_offers": True,
            "new_offers_comment": "string",
            "perception_change": True,
            "brand_compliance": 10,
            "platform_help": 5,
            "difficulties": True,
            "difficulties_comment": "string"
        }

        cls.url = reverse('collaboration')

    def test_cannot_collaborate_with_yourself(self):
        collaboration_data = {**self.collaboration_data, 'collab_with': self.brand1.id}

        response = self.auth_client1.post(self.url, collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collaboration_target_does_not_exist(self):
        collaboration_data = {**self.collaboration_data, 'collab_with': 0}

        response = self.auth_client1.post(self.url, collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collaboration_with_brand_without_match(self):
        collaboration_data = {**self.collaboration_data, 'collab_with': self.brand2.id}

        response = self.auth_client1.post(self.url, collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collaboration_create(self):
        like_url = reverse('brand-like')
        self.auth_client1.post(like_url, {'target': self.brand2.id})
        self.auth_client2.post(like_url, {'target': self.brand1.id})

        collaboration_data = {**self.collaboration_data, 'collab_with': self.brand2.id}

        response = self.auth_client1.post(self.url, collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        collab = Collaboration.objects.select_related('reporter', 'collab_with').get(pk=response.data['id'])

        self.assertEqual(collab.reporter.id, self.brand1.id)
        self.assertEqual(collab.collab_with.id, self.brand2.id)

        for key, value in self.collaboration_data.items():
            self.assertEqual(getattr(collab, key), value)

    def test_collaboration_already_reported(self):
        like_url = reverse('brand-like')
        self.auth_client1.post(like_url, {'target': self.brand2.id})
        self.auth_client2.post(like_url, {'target': self.brand1.id})

        collaboration_data = {**self.collaboration_data, 'collab_with': self.brand2.id}

        # first collab
        self.auth_client1.post(self.url, collaboration_data)

        response = self.auth_client1.post(self.url, collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collaboration_participant_can_report(self):
        like_url = reverse('brand-like')
        self.auth_client1.post(like_url, {'target': self.brand2.id})
        self.auth_client2.post(like_url, {'target': self.brand1.id})

        collaboration_data = {**self.collaboration_data, 'collab_with': self.brand2.id}

        # first collab
        self.auth_client1.post(self.url, collaboration_data)

        collaboration_data = {**self.collaboration_data, 'collab_with': self.brand1.id}

        response = self.auth_client2.post(self.url, collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        collab = Collaboration.objects.select_related('reporter', 'collab_with').get(pk=response.data['id'])

        self.assertEqual(collab.reporter.id, self.brand2.id)
        self.assertEqual(collab.collab_with.id, self.brand1.id)

        for key, value in self.collaboration_data.items():
            self.assertEqual(getattr(collab, key), value)

    def test_collaboration_activity_created_in_db(self):
        like_url = reverse('brand-like')
        self.auth_client1.post(like_url, {'target': self.brand2.id})
        self.auth_client2.post(like_url, {'target': self.brand1.id})

        collaboration_data = {**self.collaboration_data, 'collab_with': self.brand2.id}

        response = self.auth_client1.post(self.url, collaboration_data)

        collab = Collaboration.objects.prefetch_related('reporter', 'collab_with').get(pk=response.data['id'])

        self.assertTrue(MatchActivity.objects.filter(collab=collab).exists())

        activity_obj = MatchActivity.objects.select_related('initiator', 'target').get(collab=collab)

        self.assertEqual(activity_obj.initiator, self.brand1)
        self.assertEqual(activity_obj.target, self.brand2)
        self.assertTrue(activity_obj.is_match)

    def test_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {**self.collaboration_data, 'collab_with': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_brand_not_allowed(self):
        user = User.objects.create_user(
            email='user3@example.com',
            phone='+79993332213',
            fullname='Юзеров Юзер2 Юзерович',
            password='Pass!234',
            is_active=True
        )

        no_brand_auth_client = APIClient()
        no_brand_auth_client.force_authenticate(user)

        response = no_brand_auth_client.post(self.url, {**self.collaboration_data, 'collab_with': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
