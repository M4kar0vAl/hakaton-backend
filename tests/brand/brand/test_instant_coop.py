from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.models import BlackList
from core.apps.brand.factories import BrandShortFactory, LikeFactory, MatchFactory
from core.apps.chat.models import Room
from core.apps.payments.models import Subscription, Tariff


class BrandInstantCooperationTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2, cls.user3 = UserFactory.create_batch(3)
        cls.auth_client1, cls.auth_client2, cls.auth_client3 = APIClient(), APIClient(), APIClient()
        cls.auth_client1.force_authenticate(cls.user1)
        cls.auth_client2.force_authenticate(cls.user2)
        cls.auth_client3.force_authenticate(cls.user3)

        cls.business_tariff = Tariff.objects.get(name='Business Match')
        cls.lite_tariff = Tariff.objects.get(name='Lite Match')

        cls.business_tariff_relativedelta = cls.business_tariff.get_duration_as_relativedelta()
        cls.lite_tariff_relativedelta = cls.lite_tariff.get_duration_as_relativedelta()

        now = timezone.now()

        # business sub and liked brand2
        cls.brand1 = BrandShortFactory(user=cls.user1)
        Subscription.objects.create(
            brand=cls.brand1,
            tariff=cls.business_tariff,
            start_date=now,
            end_date=now + cls.business_tariff_relativedelta,
            is_active=True
        )

        # without business sub, liked brand3
        cls.brand2 = BrandShortFactory(user=cls.user2)
        Subscription.objects.create(
            brand=cls.brand2,
            tariff=cls.lite_tariff,
            start_date=now,
            end_date=now + cls.lite_tariff_relativedelta,
            is_active=True
        )

        # business sub, without like
        cls.brand3 = BrandShortFactory(user=cls.user3)
        Subscription.objects.create(
            brand=cls.brand3,
            tariff=cls.business_tariff,
            start_date=now,
            end_date=now + cls.business_tariff_relativedelta,
            is_active=True
        )

        cls.like1_2 = LikeFactory(initiator=cls.brand1, target=cls.brand2)
        cls.like2_3 = LikeFactory(initiator=cls.brand2, target=cls.brand3)

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
        BlackList.objects.create(initiator=self.brand2, blocked=self.brand1)  # brand2 blocked brand1

        # brand1 tries to instant coop brand2
        response = self.auth_client1.post(self.url, {'target': self.brand2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instant_coop_if_blocked_target_not_allowed(self):
        BlackList.objects.create(initiator=self.brand1, blocked=self.brand2)  # brand1 blocked brand2

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
        self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 instant coop brand2
        response = self.auth_client1.post(self.url, {'target': self.brand2.id})  # brand1 instant coop brand2 AGAIN

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check that another room was not created
        self.assertEqual(Room.objects.count(), 1)

    def test_instant_coop_with_match_not_allowed(self):
        MatchFactory(initiator=self.brand1, target=self.brand3)

        response = self.auth_client1.post(self.url, {'target': self.brand3.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
