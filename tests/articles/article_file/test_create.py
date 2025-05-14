from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.articles.models import ArticleFile


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
    @classmethod
    def setUpTestData(cls):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01'
            b'\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )

        cls.test_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        cls.test_unsupported_file = SimpleUploadedFile(
            'Iamsupported.txt', b'I am supported! I swear!!!', content_type='text/plain'
        )
        cls.url = reverse('tinymce_image_upload')

    def test_article_file_create(self):
        response = self.client.post(self.url, {'file': self.test_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('location' in response.data)
        self.assertEqual(ArticleFile.objects.count(), 1)

    def test_article_file_create_unsupported_file_type(self):
        response = self.client.post(self.url, {'file': self.test_unsupported_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ArticleFile.objects.count(), 0)
