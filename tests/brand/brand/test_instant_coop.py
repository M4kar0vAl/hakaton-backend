import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.factories import BlackListFactory
from core.apps.brand.factories import BrandShortFactory, MatchFactory
from core.apps.chat.models import Room
from core.apps.payments.factories import SubscriptionFactory, TariffFactory


class BrandInstantCooperationTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2, cls.user3 = UserFactory.create_batch(3)
        cls.auth_client1, cls.auth_client2, cls.auth_client3 = APIClient(), APIClient(), APIClient()
        cls.auth_client1.force_authenticate(cls.user1)
        cls.auth_client2.force_authenticate(cls.user2)
        cls.auth_client3.force_authenticate(cls.user3)

        brands = BrandShortFactory.create_batch(3, user=factory.Iterator([cls.user1, cls.user2, cls.user3]))
        (
            cls.brand1,  # business sub and liked brand2
            cls.brand2,  # without business sub, liked brand3
            cls.brand3  # business sub, without like
        ) = brands

        business_tariff = TariffFactory(business=True)
        SubscriptionFactory.create_batch(
            3,
            brand=factory.Iterator(brands),
            tariff=factory.Iterator([business_tariff, TariffFactory(lite=True), business_tariff])
        )

        cls.like1_2 = MatchFactory(like=True, initiator=cls.brand1, target=cls.brand2)
        cls.like2_3 = MatchFactory(like=True, initiator=cls.brand2, target=cls.brand3)

        cls.url = reverse('brand-instant-coop')

    def test_instant_coop_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_instant_coop_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instant_coop_wo_business_sub_not_allowed(self):
        response = self.auth_client2.post(self.url, {'target': self.brand3.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instant_coop_wo_like_not_allowed(self):
        response = self.auth_client3.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instant_coop_if_in_blacklist_of_target_not_allowed(self):
        BlackListFactory(initiator=self.brand2, blocked=self.brand1)  # brand2 blocked brand1

        # brand1 tries to instant coop brand2
        response = self.auth_client1.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instant_coop_if_blocked_target_not_allowed(self):
        BlackListFactory(initiator=self.brand1, blocked=self.brand2)  # brand1 blocked brand2

        # brand1 tries to instant coop brand2
        response = self.auth_client1.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instant_coop(self):
        response = self.auth_client1.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check that room was created
        self.assertEqual(Room.objects.count(), 1)

        room = Room.objects.prefetch_related('participants').get(pk=response.data['id'])

        # check that room type is INSTANT
        self.assertEqual(room.type, Room.INSTANT)

        # check that users were added to room participants
        self.assertTrue(self.brand1.user in room.participants.all())
        self.assertTrue(self.brand2.user in room.participants.all())

        # check that instant room was assigned to like
        self.assertIsNotNone(room.match)
        self.assertEqual(room.match.id, self.like1_2.pk)

    def test_cannot_coop_with_the_same_brand(self):
        MatchFactory(instant_coop=True, initiator=self.brand1, target=self.brand3)  # brand1 instant coop brand3

        response = self.auth_client1.post(self.url, {'target': self.brand3.id})  # brand1 instant coop brand3 AGAIN

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check that another room was not created
        self.assertEqual(Room.objects.count(), 1)

    def test_instant_coop_with_match_not_allowed(self):
        MatchFactory(initiator=self.brand1, target=self.brand3)

        response = self.auth_client1.post(self.url, {'target': self.brand3.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
