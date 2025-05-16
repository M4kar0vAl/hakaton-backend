from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.articles.models import ArticleFile

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
)
class ArticleFileCreateTestCase(APITestCase):
    @staticmethod
    def _set_user_for_client_session(client: APIClient, user: User):
        session = client.session
        session['_auth_user_id'] = user.pk
        session.save()

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            email=f'admin_user@example.com',
            phone='+79993332211',
            fullname='Админов Админ Админович',
            password='Pass!234',
            is_active=True
        )

        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.admin_user)
        cls._set_user_for_client_session(cls.auth_client, cls.admin_user)

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01'
            b'\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )

        cls.test_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        cls.test_unsupported_file = SimpleUploadedFile(
            'Iamsupported.txt', b'I am supported! I swear!!!', content_type='text/plain'
        )
        cls.url = reverse('tinymce_image_upload')

    def test_article_file_create_non_staff_not_allowed(self):
        non_staff_user = User.objects.create(
            email=f'user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        non_staff_client = APIClient()
        non_staff_client.force_authenticate(non_staff_user)
        self._set_user_for_client_session(non_staff_client, non_staff_user)

        response = non_staff_client.post(self.url, {'file': self.test_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ArticleFile.objects.count(), 0)

    def test_article_file_create(self):
        response = self.auth_client.post(self.url, {'file': self.test_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('location' in response.data)
        self.assertEqual(ArticleFile.objects.count(), 1)

    def test_article_file_create_unsupported_file_type(self):
        response = self.auth_client.post(self.url, {'file': self.test_unsupported_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ArticleFile.objects.count(), 0)
