from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile, InMemoryUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category
from core.apps.chat.models import MessageAttachment
from core.apps.payments.models import Subscription, Tariff

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
class MessageAttachmentTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

        cls.brand_data = {
            'tg_nickname': '@asfhbnaf',
            'name': 'brand1',
            'position': 'position',
            'category': Category.objects.get(pk=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        cls.brand = Brand.objects.create(user=cls.user, **cls.brand_data)
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

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01'
            b'\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )

        cls.test_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        cls.url = reverse('message_attachments')

    def test_message_attachment_create_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'file': self.test_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_message_attachment_create_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user_wo_brand@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_brand = APIClient()
        client_wo_brand.force_authenticate(user_wo_brand)

        response = client_wo_brand.post(self.url, {'file': self.test_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_message_attachment_create_wo_active_sub_not_allowed(self):
        user_wo_active_sub = User.objects.create_user(
            email='user_wo_active_sub@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        Brand.objects.create(user=user_wo_active_sub, **self.brand_data)

        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        response = client_wo_active_sub.post(self.url, {'file': self.test_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_message_attachment_create_staff_and_admins_allowed_wo_brand_and_active_sub(self):
        staff_user = User.objects.create_user(
            email='staff@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True,
            is_staff=True
        )

        superuser = User.objects.create_superuser(
            email='superuser@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        staff_client = APIClient()
        superuser_client = APIClient()

        staff_client.force_authenticate(staff_user)
        superuser_client.force_authenticate(superuser)

        staff_response = staff_client.post(self.url, {'file': self.test_file}, format='multipart')

        # If the same file is used multiple times in the same test,
        # it is needed to move file position to the beginning of the file after it was read
        self.test_file.seek(0)

        superuser_response = superuser_client.post(self.url, {'file': self.test_file}, format='multipart')

        self.assertEqual(staff_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(superuser_response.status_code, status.HTTP_201_CREATED)

        # check that objects were created in db
        self.assertTrue(MessageAttachment.objects.filter(id=staff_response.data['id']).exists())
        self.assertTrue(MessageAttachment.objects.filter(id=superuser_response.data['id']).exists())

    def test_message_attachment_create(self):
        response = self.auth_client.post(self.url, {'file': self.test_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(MessageAttachment.objects.filter(id=response.data['id']).exists())

    @patch("django.core.files.uploadhandler.MemoryFileUploadHandler.file_complete")
    def test_message_attachment_create_file_is_too_big(self, mock_file_complete):
        file_name = "big.png"
        file_content_type = "image/png"
        max_size = 1024 * 1024 * 5  # 5Mb

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

        response = self.auth_client.post(self.url, {'file': file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_file_complete.assert_called_once()

    def test_message_attachment_create_unsupported_file_type(self):
        unsupported_file_mime_type = 'text/plain'

        unsupported_file = SimpleUploadedFile(
            'unsupported', b'file content', content_type=unsupported_file_mime_type
        )

        response = self.auth_client.post(self.url, {'file': unsupported_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
