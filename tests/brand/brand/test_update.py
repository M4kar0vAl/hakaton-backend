import glob
import json
import os
import shutil

from cities_light.models import City, Country
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q
from django.test import override_settings, tag
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase

from core.apps.brand.models import Brand, Tag, ProductPhoto, Age, Gender, Category, Format, Goal

User = get_user_model()


# InMemoryStorage does not work here, because it is called from BrandUpdateSerializer.update_single_photo
# and there is another default_storage instance, which is empty.
# So default FileSystemStorage is used with overridden MEDIA_ROOT setting
# TODO try to make InMemoryStorage to work
@override_settings(MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'media', 'TEST'))
@tag('slow')
class BrandUpdateTestCase(APITransactionTestCase):  # django-cleanup requires TransactionTestCase to be used
    serialized_rollback = True

    def setUp(self):
        self.user = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )
        self.auth_client = APIClient()
        self.auth_client.force_authenticate(self.user)

        self.country = Country.objects.create(name='Country', continent='EU')
        self.city1 = City.objects.create(name='City1', country=self.country)
        self.city2 = City.objects.create(name='City2', country=self.country)
        self.city3 = City.objects.create(name='City3', country=self.country)

        # create brand-new brand before each test
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01'
            b'\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        logo_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        photo_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file1 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file2 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')
        product_file3 = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')

        data = {
            'tg_nickname': '@asfhbnaf',
            'blogs_list': json.dumps(["https://example.com", "https://example2.com"]),
            'city': self.city1.id,
            'name': 'brand1',
            'position': 'position',
            'category': json.dumps({"name": "Fashion"}),
            'inst_url': 'https://example.com',
            'vk_url': 'https://example.com',
            'tg_url': 'https://example.com',
            'wb_url': 'https://example.com',
            'lamoda_url': 'https://example.com',
            'site_url': 'https://example.com',
            'subs_count': 10000,
            'avg_bill': 10000,
            'tags': json.dumps([
                {"name": "Свобода", "is_other": False},
                {"name": "Минимализм"},
                {"name": "Любовь"},
                {"name": "Самобытность"},
                {"name": "Активность"},
                {"name": "other", "is_other": True}
            ]),
            'uniqueness': 'uniqueness',
            'logo': logo_file,
            'photo': photo_file,
            'product_photos_match': [product_file, product_file1],
            'product_photos_card': [product_file2, product_file3]
        }

        response = self.auth_client.post(reverse('brand-list'), data, format='multipart')
        self.brand = Brand.objects.get(id=response.data['id'])
        self.url = reverse('brand-me')

    def tearDown(self):
        # delete created media files after each test
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT))

    def test_brand_put_not_allowed(self):
        response = self.auth_client.put(self.url, {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_brand_update_unauthenticated_not_allowed(self):
        response = self.client.patch(self.url, {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_brand_update_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user2@example.com',
            phone='+79993332212',
            fullname='Юзеров Юзер1 Юзерович',
            password='Pass!234',
            is_active=True
        )
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)
        response = auth_client_wo_brand.patch(self.url, {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_brand_partial_update_whole_data(self):
        other_small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        logo_file = SimpleUploadedFile('small.gif', other_small_gif, content_type='image/gif')
        photo_file = SimpleUploadedFile('small.gif', other_small_gif, content_type='image/gif')
        product_file = SimpleUploadedFile('small.gif', other_small_gif, content_type='image/gif')
        product_file1 = SimpleUploadedFile('small.gif', other_small_gif, content_type='image/gif')
        gallery_photo1 = SimpleUploadedFile('small.gif', other_small_gif, content_type='image/gif')
        gallery_photo2 = SimpleUploadedFile('small.gif', other_small_gif, content_type='image/gif')

        update_data = {
            'tg_nickname': '@edited',
            'new_blogs': json.dumps(["https://edited.com", "https://edited.com"]),
            'city': self.city2.id,
            'name': 'edited',
            'position': 'edited',
            'category': json.dumps({"name": "Services"}),
            'inst_url': 'https://edited.com',
            'vk_url': 'https://edited.com',
            'tg_url': 'https://edited.com',
            'wb_url': 'https://edited.com',
            'lamoda_url': 'https://edited.com',
            'site_url': 'https://edited.com',
            'subs_count': 100000,
            'avg_bill': 100000,
            'tags': json.dumps([
                {"name": "Высокое качество", "is_other": False},
                {"name": "Социальная значимость"},
                {"name": "other_other", "is_other": True}
            ]),
            'uniqueness': 'edited',
            'logo': logo_file,
            'photo': photo_file,
            'product_photos_match_add': [product_file],
            'product_photos_match_remove': json.dumps(
                list(self.brand.product_photos.filter(format=ProductPhoto.MATCH).values_list('id', flat=True))
            ),  # remove all photos
            'product_photos_card_add': [product_file1],
            'product_photos_card_remove': json.dumps(
                list(self.brand.product_photos.filter(format=ProductPhoto.CARD).values_list('id', flat=True))
            ),  # remove all photos
            'mission_statement': 'mission_statement',
            'formats': json.dumps([
                {"name": "Продукт"},
                {"name": "other", "is_other": True}
            ]),
            'goals': json.dumps([
                {"name": "Продажи"},
                {"name": "other", "is_other": True}
            ]),
            'offline_space': 'offline_space',
            'problem_solving': 'problem_solving',
            'target_audience': json.dumps({
                "age": {"men": 30, "women": 40},
                "gender": {"men": 30, "women": 70},
                "geos": [
                    {"city": self.city1.id, "people_percentage": 40},
                    {"city": self.city2.id, "people_percentage": 60}
                ],
                "income": 50000
            }),
            'categories_of_interest': json.dumps([
                {"name": "HoReCa"},
                {"name": "Kids"},
                {"name": "other", "is_other": True}
            ]),
            'new_business_groups': json.dumps(["name", "https://example.com"]),
            'gallery_add': [gallery_photo1, gallery_photo2]
        }

        response = self.auth_client.patch(self.url, update_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_brand = Brand.objects.select_related(
            'category',
            'target_audience__age',
            'target_audience__gender'
        ).get(pk=self.brand.id)

        # check simple fields
        self.assertEqual(updated_brand.tg_nickname, '@edited')
        self.assertEqual(updated_brand.name, 'edited')
        self.assertEqual(updated_brand.position, 'edited')
        self.assertEqual(updated_brand.inst_url, 'https://edited.com')
        self.assertEqual(updated_brand.vk_url, 'https://edited.com')
        self.assertEqual(updated_brand.tg_url, 'https://edited.com')
        self.assertEqual(updated_brand.wb_url, 'https://edited.com')
        self.assertEqual(updated_brand.lamoda_url, 'https://edited.com')
        self.assertEqual(updated_brand.site_url, 'https://edited.com')
        self.assertEqual(updated_brand.subs_count, 100000)
        self.assertEqual(updated_brand.avg_bill, 100000)
        self.assertEqual(updated_brand.uniqueness, 'edited')
        self.assertEqual(updated_brand.mission_statement, 'mission_statement')
        self.assertEqual(updated_brand.offline_space, 'offline_space')
        self.assertEqual(updated_brand.problem_solving, 'problem_solving')

        # check blogs
        self.assertEqual(updated_brand.blogs.count(), 2)
        self.assertEqual(updated_brand.blogs.filter(blog__in=["https://edited.com", "https://edited.com"]).count(), 2)

        # check city
        self.assertEqual(updated_brand.city.id, self.city2.id)

        # check category
        self.assertEqual(updated_brand.category.name, 'Services')

        # check tags
        self.assertEqual(updated_brand.tags.count(), 3)
        self.assertEqual(updated_brand.tags.filter(
            name__in=['Высокое качество', 'Социальная значимость', 'other_other']
        ).count(), 3)
        self.assertEqual(updated_brand.tags.filter(is_other=True).count(), 1)

        # check formats
        self.assertEqual(updated_brand.formats.count(), 2)
        self.assertEqual(updated_brand.formats.filter(name__in=['Продукт', 'other']).count(), 2)
        self.assertEqual(updated_brand.formats.filter(is_other=True).count(), 1)

        # check goals
        self.assertEqual(updated_brand.goals.count(), 2)
        self.assertEqual(updated_brand.goals.filter(name__in=['Продажи', 'other']).count(), 2)
        self.assertEqual(updated_brand.goals.filter(is_other=True).count(), 1)

        # check categories of interest
        self.assertEqual(updated_brand.categories_of_interest.count(), 3)
        self.assertEqual(updated_brand.categories_of_interest.filter(name__in=['HoReCa', 'Kids', 'other']).count(), 3)
        self.assertEqual(updated_brand.categories_of_interest.filter(is_other=True).count(), 1)

        # check business groups
        self.assertEqual(updated_brand.business_groups.count(), 2)
        self.assertEqual(updated_brand.business_groups.filter(name__in=["name", "https://example.com"]).count(), 2)

        # check target audience
        self.assertIsNotNone(updated_brand.target_audience)
        self.assertIsNotNone(updated_brand.target_audience.age)
        self.assertIsNotNone(updated_brand.target_audience.gender)
        self.assertIsNotNone(updated_brand.target_audience.income)
        self.assertEqual(updated_brand.target_audience.age.men, 30)
        self.assertEqual(updated_brand.target_audience.age.women, 40)
        self.assertEqual(updated_brand.target_audience.gender.men, 30)
        self.assertEqual(updated_brand.target_audience.gender.women, 70)
        self.assertEqual(updated_brand.target_audience.income, 50000)
        self.assertEqual(updated_brand.target_audience.geos.count(), 2)
        self.assertEqual(updated_brand.target_audience.geos.filter(
            Q(city=self.city1, people_percentage=40) | Q(city=self.city2, people_percentage=60)
        ).count(), 2)

        # check single photos
        logo_files = glob.glob(os.path.join(settings.MEDIA_ROOT, f'user_{self.user.id}', 'logo*'))
        photo_files = glob.glob(os.path.join(settings.MEDIA_ROOT, f'user_{self.user.id}', 'photo*'))

        self.assertEqual(len(logo_files), 1)
        self.assertEqual(len(photo_files), 1)

        # check that files actually changed by comparing their sizes
        self.assertEqual(
            default_storage.size(logo_files[0]),
            37
        )
        self.assertEqual(
            default_storage.size(photo_files[0]),
            37
        )

        # check gallery
        files = glob.glob(os.path.join(settings.MEDIA_ROOT, f'user_{self.user.id}', 'gallery', '*'))
        self.assertEqual(len(files), 2)
        self.assertEqual(updated_brand.gallery_photos.count(), 2)

        for path in files:
            # check that files actually changed by comparing their sizes
            self.assertEqual(default_storage.size(path), 37)

        # check product photos
        match_files = glob.glob(os.path.join(
            settings.MEDIA_ROOT, f'user_{self.user.id}', 'product_photos', 'match', '*')
        )
        card_files = glob.glob(os.path.join(
            settings.MEDIA_ROOT, f'user_{self.user.id}', 'product_photos', 'brand_card', '*')
        )

        for path in match_files + card_files:
            # check that files actually changed by comparing their sizes
            self.assertEqual(default_storage.size(path), 37)

        self.assertEqual(len(match_files), 1)
        self.assertEqual(len(card_files), 1)
        self.assertEqual(updated_brand.product_photos.count(), 2)
        self.assertEqual(updated_brand.product_photos.filter(format=ProductPhoto.CARD).count(), 1)
        self.assertEqual(updated_brand.product_photos.filter(format=ProductPhoto.MATCH).count(), 1)

    def test_brand_gallery_photos_remove(self):
        other_small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        gallery_photo1 = SimpleUploadedFile('small.gif', other_small_gif, content_type='image/gif')
        gallery_photo2 = SimpleUploadedFile('small.gif', other_small_gif, content_type='image/gif')

        # add photos to initial data
        self.auth_client.patch(self.url, {
            'gallery_add': [gallery_photo1, gallery_photo2]
        }, format='multipart')

        ids_to_remove = self.brand.gallery_photos.values_list('id', flat=True)

        response = self.auth_client.patch(self.url, {
            'gallery_remove': json.dumps(list(ids_to_remove))
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.brand.gallery_photos.exists())
        self.assertEqual(len(glob.glob(os.path.join(settings.MEDIA_ROOT, f'user_{self.user.id}', 'gallery', '*'))), 0)

    def test_brand_target_audience_remove_fields(self):
        data = {
            'target_audience': json.dumps({
                "age": {"men": 30, "women": 40},
                "gender": {"men": 30, "women": 70},
                "geos": [
                    {"city": self.city1.id, "people_percentage": 40},
                    {"city": self.city2.id, "people_percentage": 60}
                ],
                "income": 50000
            })
        }

        # set up target audience
        self.auth_client.patch(self.url, data)

        response = self.auth_client.patch(self.url, {
            'target_audience': json.dumps({
                "age": {},
                "gender": {},
                "geos": [],
                "income": None
            })
        })

        updated_brand = Brand.objects.select_related(
            'target_audience__age',
            'target_audience__gender'
        ).get(pk=self.brand.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(updated_brand.target_audience)
        self.assertIsNone(updated_brand.target_audience.age)
        self.assertIsNone(updated_brand.target_audience.gender)
        self.assertIsNone(updated_brand.target_audience.income)
        self.assertFalse(Age.objects.filter(target_audience=updated_brand.target_audience).exists())
        self.assertFalse(Gender.objects.filter(target_audience=updated_brand.target_audience).exists())
        self.assertFalse(updated_brand.target_audience.geos.all().exists())

    def test_brand_target_audience_update(self):
        data = {
            'target_audience': json.dumps({
                "age": {"men": 30, "women": 40},
                "gender": {"men": 30, "women": 70},
                "geos": [
                    {"city": self.city1.id, "people_percentage": 40},
                    {"city": self.city2.id, "people_percentage": 60}
                ],
                "income": 50000
            })
        }

        # set up target audience
        self.auth_client.patch(self.url, data)

        update_data = {
            'target_audience': json.dumps({
                "age": {"men": 40, "women": 35},
                "gender": {"men": 20, "women": 80},
                "geos": [
                    {"city": self.city1.id, "people_percentage": 50},
                    {"city": self.city3.id, "people_percentage": 50}
                ],
                "income": 60000
            })
        }

        response = self.auth_client.patch(self.url, update_data)

        updated_brand = Brand.objects.select_related(
            'target_audience__age',
            'target_audience__gender'
        ).get(pk=self.brand.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(updated_brand.target_audience.age.men, 40)
        self.assertEqual(updated_brand.target_audience.age.women, 35)
        self.assertEqual(Age.objects.filter(target_audience=updated_brand.target_audience).count(), 1)

        self.assertEqual(updated_brand.target_audience.gender.men, 20)
        self.assertEqual(updated_brand.target_audience.gender.women, 80)
        self.assertEqual(Gender.objects.filter(target_audience=updated_brand.target_audience).count(), 1)

        self.assertEqual(updated_brand.target_audience.income, 60000)

        self.assertEqual(updated_brand.target_audience.geos.count(), 2)
        self.assertEqual(updated_brand.target_audience.geos.filter(
            Q(city=self.city1, people_percentage=50) | Q(city=self.city3, people_percentage=50)
        ).count(), 2)

    def test_brand_remove_all_tags(self):
        response = self.auth_client.patch(self.url, {
            'tags': json.dumps([])
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_brand_remove_all_to_many_fields_except_tags_and_photos(self):
        self.auth_client.patch(self.url, {
            'formats': json.dumps([
                {"name": "Продукт"},
                {"name": "other", "is_other": True}
            ]),
            'goals': json.dumps([
                {"name": "Продажи"},
                {"name": "other", "is_other": True}
            ]),
            'categories_of_interest': json.dumps([
                {"name": "HoReCa"},
                {"name": "Kids"},
                {"name": "other", "is_other": True}
            ]),
            'new_business_groups': json.dumps(["name", "https://example.com"])
        })

        response = self.auth_client.patch(self.url, {
            'goals': json.dumps([]),
            'formats': json.dumps([]),
            'categories_of_interest': json.dumps([]),
            'new_blogs': json.dumps([]),
            'new_business_groups': json.dumps([])
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(self.brand.goals.exists())
        self.assertFalse(self.brand.formats.exists())
        self.assertFalse(self.brand.categories_of_interest.exists())
        self.assertFalse(self.brand.blogs.exists())
        self.assertFalse(self.brand.business_groups.exists())

    def test_brand_fields_with_other_option(self):
        self.auth_client.patch(self.url, {
            'category': json.dumps({'name': 'other', 'is_other': True}),
            'formats': json.dumps([
                {"name": "Продукт"},
                {"name": "other", "is_other": True}
            ]),
            'goals': json.dumps([
                {"name": "Продажи"},
                {"name": "other", "is_other": True}
            ]),
            'categories_of_interest': json.dumps([
                {"name": "HoReCa"},
                {"name": "Kids"},
                {"name": "other", "is_other": True}
            ])
        })

        categories_before = int(Category.objects.count())
        formats_before = int(Format.objects.count())
        goals_before = int(Goal.objects.count())
        tags_before = int(Tag.objects.count())

        response = self.auth_client.patch(self.url, {
            'category': json.dumps({'name': 'other_other', 'is_other': True}),
            'tags': json.dumps([
                {"name": "Свобода", "is_other": False},
                {"name": "Минимализм"},
                {"name": "Любовь"},
                {"name": "Самобытность"},
                {"name": "Активность"},
                {"name": "other_other", "is_other": True}
            ]),
            'formats': json.dumps([
                {"name": "Продукт"},
                {"name": "other_other", "is_other": True}
            ]),
            'goals': json.dumps([
                {"name": "Продажи"},
                {"name": "other_other", "is_other": True}
            ]),
            'categories_of_interest': json.dumps([
                {"name": "HoReCa"},
                {"name": "Kids"},
                {"name": "other_other", "is_other": True}
            ])
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated_brand = Brand.objects.select_related('category').get(pk=self.brand.id)

        # check category
        self.assertEqual(categories_before, Category.objects.count())
        self.assertEqual(updated_brand.category.name, 'other_other'),
        self.assertTrue(updated_brand.category.is_other)
        self.assertEqual(Category.objects.filter(brands__in=[self.brand.id], is_other=True).count(), 1)

        # check tags
        self.assertEqual(tags_before, Tag.objects.count())
        self.assertEqual(updated_brand.tags.count(), 6)
        tags = [
            {"name": "Свобода", "is_other": False},
            {"name": "Минимализм"},
            {"name": "Любовь"},
            {"name": "Самобытность"},
            {"name": "Активность"},
            {"name": "other_other", "is_other": True}
        ]
        query = Q(**tags[0])
        for tag in tags[1:]:
            query |= Q(**tag)
        self.assertEqual(updated_brand.tags.filter(query).count(), 6)

        # check formats
        self.assertEqual(formats_before, Format.objects.count())
        self.assertEqual(updated_brand.formats.count(), 2)
        self.assertEqual(
            updated_brand.formats.filter(Q(name='Продукт') | Q(name='other_other', is_other=True)).count(),
            2
        )

        # check goals
        self.assertEqual(goals_before, Goal.objects.count())
        self.assertEqual(updated_brand.goals.count(), 2)
        self.assertEqual(
            updated_brand.goals.filter(Q(name='Продажи') | Q(name='other_other', is_other=True)).count(),
            2
        )

        # check categories of interest
        self.assertEqual(updated_brand.categories_of_interest.count(), 3)
        self.assertEqual(
            updated_brand.categories_of_interest.filter(
                Q(name='HoReCa') | Q(name='Kids') | Q(name='other_other', is_other=True)
            ).count(),
            3
        )
