import datetime
from io import BytesIO

from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand
from core.apps.payments.models import Subscription

User = get_user_model()


class BoardTestCase(APITestCase):
    def setUp(self):
        user_data = {
            'email': 'user1@example.com',
            'phone': '+79993332211',
            'password': 'Pass!234',
            'is_active': True,
        }
        self.user = User.objects.create_user(**user_data)
        self.client = APIClient()
        self.auth_client = APIClient()
        self.auth_client.force_authenticate(self.user)
        self.brand = Brand.objects.create(
            user=self.user,
            published=True,
            subscription=None,
            sub_expire=None,
            tg_nickname='@telegram',
            phone='+79998884422',
            brand_name_pos='text',
            inst_brand_url='text text',
            brand_site_url='text text',
            topics='темы',
            mission_statement='text',
            target_audience='text',
            unique_product_is='text',
            product_description='text text',
            problem_solving='text text',
            business_group='text text',
            logo='Лого',
            photo='Фото представителя',
            product_photo='Фото продукта',
            fullname='text',
            email='email@example.com',
        )

    def test_create_brand(self):
        logo = BytesIO(b'logo')
        photo = BytesIO(b'photo')
        prod_photo = BytesIO(b'prod_photo')
        data = {
            "category": {
                "text": "Красота и здоровье",
                "question": 4,
            },
            "presence_type": {
                "text": "Online",
                "question": 7,
            },
            "public_speaker": {
                "text": "Да",
                "question": 9,
            },
            "subs_count": {
                "text": "100.000 - 500.000",
                "question": 10,
            },
            "avg_bill": {
                "text": "1.000 - 10.000",
                "question": 11,
            },
            "goals": [
                {
                    "text": "Свой вариант: У самурая нет цели, только путь",
                    "question": 18,
                },
                {
                    "text": "Рост продаж",
                    "question": 18,
                },
                {
                    "text": "Другое",
                    "question": 18,
                }
            ],
            "formats": [
                {
                    "text": "Совместный reels",
                    "question": 17,
                }
            ],
            "collaboration_interest": [
                {
                    "text": "Я открыта к экспериментам и категория партнера мне не важна",
                    "question": 19,
                }
            ],
            "tg_nickname": "text test",
            "phone": "text test",
            "brand_name_pos": "text test",
            "inst_brand_url": "text test",
            "brand_site_url": "text test",
            "topics": "text test",
            "mission_statement": "text test",
            "target_audience": "text test",
            "unique_product_is": "text test",
            "product_description": "text test",
            "problem_solving": "text test",
            "business_group": "text test",
            "fullname": "text test",
            "email": "example@mail.ru",
            'logo': logo,
            'photo': photo,
            'product_photo': prod_photo,
        }

        response = self.auth_client.get(reverse('payments-list'))
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(Brand.objects.all()))
