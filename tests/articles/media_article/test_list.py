import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.articles.factories import MediaArticleFactory
from core.apps.brand.factories import BrandShortFactory
from tests.factories import APIClientFactory


class MediaArticleListTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(has_sub=True)
        cls.auth_client = APIClientFactory(user=cls.user)

        cls.published_media_article, cls.unpublished_media_article = MediaArticleFactory.create_batch(
            2, is_published=factory.Iterator([True, False])
        )

        cls.url = reverse('media_articles-list')

    def test_media_article_list_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_media_article_list_user_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        client_wo_brand = APIClientFactory(user=user_wo_brand)

        response = client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_media_article_list_user_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClientFactory(user=user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_media_article_list(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.published_media_article.id)
