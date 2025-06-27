from unittest.mock import patch

import factory
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile, InMemoryUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.chat.factories import MessageAttachmentFactory
from core.apps.chat.models import MessageAttachment
from core.apps.payments.factories import SubscriptionFactory
from tests.utils import refresh_api_settings


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
class MessageAttachmentTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        refresh_api_settings()

        cls.user = UserFactory()
        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)
        cls.brand = BrandShortFactory(user=cls.user)

        SubscriptionFactory(brand=cls.brand)

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01'
            b'\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )

        cls.test_file = factory.build(
            dict, FACTORY_CLASS=MessageAttachmentFactory, file__data=small_gif, file__filename='f.gif'
        )['file']
        cls.url = reverse('message_attachments')

    def test_message_attachment_create_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'file': self.test_file})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_message_attachment_create_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        client_wo_brand = APIClient()
        client_wo_brand.force_authenticate(user_wo_brand)

        response = client_wo_brand.post(self.url, {'file': self.test_file})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_message_attachment_create_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.post(self.url, {'file': self.test_file})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_message_attachment_create_staff_and_admins_allowed_wo_brand_and_active_sub(self):
        staff_user = UserFactory(staff=True)
        staff_client = APIClient()
        staff_client.force_authenticate(staff_user)

        superuser = UserFactory(admin=True)
        superuser_client = APIClient()
        superuser_client.force_authenticate(superuser)

        staff_response = staff_client.post(self.url, {'file': self.test_file})

        # If the same file is used multiple times in the same test,
        # it is needed to move file position to the beginning of the file after it was read
        self.test_file.seek(0)

        superuser_response = superuser_client.post(self.url, {'file': self.test_file})

        self.assertEqual(staff_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(superuser_response.status_code, status.HTTP_201_CREATED)

        # check that objects were created in db
        self.assertTrue(MessageAttachment.objects.filter(id=staff_response.data['id']).exists())
        self.assertTrue(MessageAttachment.objects.filter(id=superuser_response.data['id']).exists())

    def test_message_attachment_create(self):
        response = self.auth_client.post(self.url, {'file': self.test_file})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(MessageAttachment.objects.filter(id=response.data['id']).exists())

    @patch("django.core.files.uploadhandler.MemoryFileUploadHandler.file_complete")
    def test_message_attachment_create_file_is_too_big(self, mock_file_complete):
        file_name = "big.png"
        file_content_type = "image/png"
        max_size = settings.MESSAGE_ATTACHMENT_MAX_SIZE

        mock_file_complete.return_value = InMemoryUploadedFile(
            file=b"",
            field_name=None,
            name=file_name,
            content_type=file_content_type,
            size=max_size + 1,
            charset=None,
        )

        file = SimpleUploadedFile(
            name=file_name,
            content=b"",
            content_type=file_content_type,
        )

        response = self.auth_client.post(self.url, {'file': file})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_file_complete.assert_called_once()

    def test_message_attachment_create_unsupported_file_type(self):
        unsupported_file = factory.build(dict, FACTORY_CLASS=MessageAttachmentFactory)['file']

        response = self.auth_client.post(self.url, {'file': unsupported_file})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
