from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.articles.models import Tutorial, Article
from core.apps.brand.models import Brand, Category
from core.apps.payments.models import Tariff, Subscription

User = get_user_model()


class TutorialListTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(
            email=f'user@example.com',
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

        articles = Article.objects.bulk_create([
            Article(content='some <b>content</b>'),
            Article(content='some <b>content 2</b>')
        ])

        cls.published_tutorial, cls.unpublished_tutorial = Tutorial.objects.bulk_create([
            Tutorial(
                title='asfa',
                excerpt='asfaegk',
                preview='path/to/file',
                body=articles[0],
                is_published=True  # must be returned
            ),
            Tutorial(
                title='asfa',
                excerpt='asfaegk',
                preview='path/to/file',
                body=articles[1],
                is_published=False  # must not be returned
            ),
        ])

        cls.url = reverse('tutorials-list')

    def test_tutorial_list_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tutorial_list_user_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create(
            email=f'user_wo_brand@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_brand = APIClient()
        client_wo_brand.force_authenticate(user_wo_brand)

        response = client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tutorial_list_user_wo_active_sub_not_allowed(self):
        user_wo_active_sub = User.objects.create(
            email=f'user_wo_active_sub@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        Brand.objects.create(user=user_wo_active_sub, **self.brand_data)

        response = client_wo_active_sub.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tutorial_list(self):
        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.published_tutorial.id)
