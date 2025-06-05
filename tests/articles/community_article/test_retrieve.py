import factory
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.articles.factories import CommunityArticleFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.models import Tariff, Subscription


class CommunityArticleRetrieveTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)
        cls.brand = BrandShortFactory(user=cls.user)

        cls.tariff = Tariff.objects.get(name='Business Match')
        cls.tariff_relativedelta = cls.tariff.get_duration_as_relativedelta()
        now = timezone.now()

        Subscription.objects.create(
            brand=cls.brand,
            tariff=cls.tariff,
            start_date=now,
            end_date=now + cls.tariff_relativedelta,
            is_active=True
        )

        cls.published_community_article, cls.unpublished_community_article = CommunityArticleFactory.create_batch(
            2, is_published=factory.Iterator([True, False])
        )

        cls.published_community_article_url = reverse(
            'community_articles-detail', kwargs={'pk': cls.published_community_article.pk}
        )
        cls.unpublished_community_article_url = reverse(
            'community_articles-detail', kwargs={'pk': cls.unpublished_community_article.pk}
        )

    def test_community_article_retrieve_unauthenticated_not_allowed(self):
        response = self.client.get(self.published_community_article_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_community_article_retrieve_user_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        client_wo_brand = APIClient()
        client_wo_brand.force_authenticate(user_wo_brand)

        response = client_wo_brand.get(self.published_community_article_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_community_article_retrieve_user_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.get(self.published_community_article_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_community_article_retrieve(self):
        response = self.auth_client.get(self.published_community_article_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['body']['content'], self.published_community_article.body.content)

    def test_community_article_retrieve_unpublished(self):
        response = self.auth_client.get(self.unpublished_community_article_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
