import factory
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.articles.factories import ArticleFileFactory
from core.apps.articles.models import ArticleFile
from tests.utils import refresh_api_settings

User = get_user_model()


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
    REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        'TEST_REQUEST_DEFAULT_FORMAT': 'multipart',
    }
)
class ArticleFileCreateTestCase(APITestCase):
    @staticmethod
    def _set_user_for_client_session(client: APIClient, user: User):
        session = client.session
        session['_auth_user_id'] = user.pk
        session.save()

    @classmethod
    def setUpTestData(cls):
        refresh_api_settings()

        cls.admin_user = UserFactory(admin=True)
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.admin_user)
        cls._set_user_for_client_session(cls.auth_client, cls.admin_user)

        cls.test_file = factory.build(dict, FACTORY_CLASS=ArticleFileFactory)['file']
        cls.test_unsupported_file = factory.build(dict, FACTORY_CLASS=ArticleFileFactory, file__format='ICO')['file']

        cls.url = reverse('tinymce_image_upload')

    def test_article_file_create_non_staff_not_allowed(self):
        non_staff_user = UserFactory()
        non_staff_client = APIClient()
        non_staff_client.force_authenticate(non_staff_user)
        self._set_user_for_client_session(non_staff_client, non_staff_user)

        response = non_staff_client.post(self.url, {'file': self.test_file})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ArticleFile.objects.count(), 0)

    def test_article_file_create(self):
        response = self.auth_client.post(self.url, {'file': self.test_file})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('location' in response.data)
        self.assertEqual(ArticleFile.objects.count(), 1)

    def test_article_file_create_unsupported_file_type(self):
        response = self.auth_client.post(self.url, {'file': self.test_unsupported_file})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ArticleFile.objects.count(), 0)
