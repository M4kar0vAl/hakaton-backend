import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.factories import BlackListFactory
from core.apps.brand.factories import BrandShortFactory, MatchFactory
from core.apps.brand.models import Match
from core.apps.chat.models import Room


class BrandLikeTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2 = UserFactory.create_batch(2)
        cls.auth_client1, cls.auth_client2 = APIClient(), APIClient()
        cls.auth_client1.force_authenticate(cls.user1)
        cls.auth_client2.force_authenticate(cls.user2)
        cls.brand1, cls.brand2 = BrandShortFactory.create_batch(
            2, user=factory.Iterator([cls.user1, cls.user2]), has_sub=True
        )

        cls.url = reverse('brand-like')

    def test_like_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_like_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_like_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.post(self.url, {'target': self.brand1.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_like_if_in_blacklist_of_target_not_allowed(self):
        BlackListFactory(initiator=self.brand2, blocked=self.brand1)  # brand2 blocked brand1

        response = self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 tries to like brand2

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_like_if_blocked_target_not_allowed(self):
        BlackListFactory(initiator=self.brand1, blocked=self.brand2)  # brand1 blocked brand2

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
        MatchFactory(like=True, initiator=self.brand1, target=self.brand2)  # brand1 likes brand2
        response = self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 likes brand2 AGAIN

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_like_each_other_leads_to_match(self):
        MatchFactory(like=True, initiator=self.brand1, target=self.brand2)  # brand1 likes brand2
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
        MatchFactory(initiator=self.brand1, target=self.brand2)  # brand1 has match with brand2

        response = self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 likes brand2 AGAIN

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Match.objects.count(), 1)

    def test_like_not_existing_brand(self):
        response = self.auth_client1.post(self.url, {'target': 0})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_like_in_response_if_instant_cooped(self):
        # brand1 instant coop brand2
        instant_coop = MatchFactory(instant_coop=True, initiator=self.brand1, target=self.brand2)
        response = self.auth_client2.post(self.url, {'target': self.brand1.id})  # brand2 likes brand1 MATCH

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        room_id = response.data['room']

        # check that id of the room did not change
        self.assertEqual(room_id, instant_coop.room_id)

        # check that room type was changed to MATCH
        room = Room.objects.get(id=room_id)
        self.assertEqual(room.type, Room.MATCH)
