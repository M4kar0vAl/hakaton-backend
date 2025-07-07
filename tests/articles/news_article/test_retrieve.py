import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.articles.factories import NewsArticleFactory
from core.apps.brand.factories import BrandShortFactory
from tests.factories import APIClientFactory


class NewsArticleRetrieveTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(has_sub=True)
        cls.auth_client = APIClientFactory(user=cls.user)

        cls.published_news_article, cls.unpublished_news_article = NewsArticleFactory.create_batch(
            2, is_published=factory.Iterator([True, False])
        )

        cls.published_news_article_url = reverse(
            'news_articles-detail', kwargs={'pk': cls.published_news_article.pk}
        )
        cls.unpublished_news_article_url = reverse(
            'news_articles-detail', kwargs={'pk': cls.unpublished_news_article.pk}
        )

    def test_news_article_retrieve_unauthenticated_not_allowed(self):
        response = self.client.get(self.published_news_article_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_news_article_retrieve_user_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        client_wo_brand = APIClientFactory(user=user_wo_brand)

        response = client_wo_brand.get(self.published_news_article_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_news_article_retrieve_user_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClientFactory(user=user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.get(self.published_news_article_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_news_article_retrieve(self):
        response = self.auth_client.get(self.published_news_article_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['body']['content'], self.published_news_article.body.content)

    def test_news_article_retrieve_unpublished(self):
        response = self.auth_client.get(self.unpublished_news_article_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
