import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.factories import GiftPromoCodeFactory, TariffFactory, SubscriptionFactory
from core.apps.payments.models import GiftPromoCode
from tests.factories import APIClientFactory


class GiftPromoCodeActivateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2 = UserFactory.create_batch(2)
        cls.giver_auth_client, cls.receiver_auth_client = APIClientFactory.create_batch(
            2, user=factory.Iterator([cls.user1, cls.user2])
        )

        cls.giver_brand = BrandShortFactory(user=cls.user1)
        cls.receiver_brand = BrandShortFactory(user=cls.user2)

        cls.valid_lite_gift = GiftPromoCodeFactory(giver=cls.giver_brand, tariff=TariffFactory(lite=True))
        cls.valid_business_gift = GiftPromoCodeFactory(giver=cls.giver_brand)
        cls.used_gift = GiftPromoCodeFactory(giver=cls.giver_brand, is_used=True)
        cls.expired_gift = GiftPromoCodeFactory(giver=cls.giver_brand, expired=True)

        cls.url = reverse('gift_promocodes-activate')

    def test_activate_gift_promocode_unauthenticated_now_allowed(self):
        response = self.client.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_activate_gift_promocode_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClientFactory(user=user_wo_brand)

        response = auth_client_wo_brand.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_activate_gift_promocode_with_active_subscription(self):
        SubscriptionFactory(brand=self.receiver_brand)
        response = self.receiver_auth_client.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_gift_promocode_cannot_use_own_gift(self):
        response = self.giver_auth_client.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_gift_promocode_already_used(self):
        response = self.receiver_auth_client.post(self.url, {'gift_promocode': self.used_gift.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_gift_promocode_already_expired(self):
        response = self.receiver_auth_client.post(self.url, {'gift_promocode': self.expired_gift.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_gift_promocode(self):
        response = self.receiver_auth_client.post(self.url, {'gift_promocode': self.valid_lite_gift.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.receiver_brand.subscriptions.count(), 1)

        # check that subscription was bound to gift promo code
        self.assertEqual(self.receiver_brand.subscriptions.get().gift_promocode.id, self.valid_lite_gift.id)

        # check that correct tariff was applied
        self.assertEqual(response.data['tariff']['id'], self.valid_lite_gift.tariff_id)

        # check that promocode wasn't used
        self.assertIsNone(response.data['promocode'])

        # check that gifted subscription is activated
        self.assertTrue(response.data['is_active'])

    def test_activate_gift_promocode_cannot_activate_twice_same_gift(self):
        sub = SubscriptionFactory(brand=self.receiver_brand, is_gifted=True)
        gift_id = sub.gift_promocode_id

        response = self.receiver_auth_client.post(self.url, {'gift_promocode': gift_id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check that gift promo code is marked as used
        self.assertTrue(GiftPromoCode.objects.get(id=gift_id).is_used)
