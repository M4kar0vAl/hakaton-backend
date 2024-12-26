from cities_light.models import Country, City
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.brand.models import Brand, Category, Format, Tag, Goal
from tests.mixins import AssertNumQueriesLessThanMixin

User = get_user_model()


class BrandRecommendedBrandsTestCase(
    APITestCase,
    AssertNumQueriesLessThanMixin
):
    @classmethod
    def setUpTestData(cls):
        users = User.objects.bulk_create([
            User(
                email=f'user{i}@example.com',
                phone='+79993332211',
                fullname='Юзеров Юзер Юзерович',
                password='Pass!234',
                is_active=True
            ) for i in range(1, 11)
        ])

        for i, user in enumerate(users, start=1):
            # set users to class attributes named user{i}
            setattr(cls, f'user{i}', user)

            # create APIClient instance for each user
            setattr(cls, f'auth_client{i}', APIClient())

            # force authenticate clients
            getattr(cls, f'auth_client{i}').force_authenticate(user)

        cls.formats = list(Format.objects.order_by('id'))
        cls.categories = list(Category.objects.order_by('id'))
        cls.tags = list(Tag.objects.order_by('id'))
        cls.goals = list(Goal.objects.order_by('id'))

        cls.country = Country.objects.create(name='Country', continent='EU')
        cls.city1 = City.objects.create(name='City1', country=cls.country)
        cls.city2 = City.objects.create(name='City2', country=cls.country)
        cls.city3 = City.objects.create(name='City3', country=cls.country)

        # formats, categories, tags, goals, avg_bill, subs_count
        cls.brand_data = {
            'tg_nickname': '@asfhbnaf',
            'city': cls.city1,
            'name': 'brand1',
            'position': 'position',
            'category': cls.categories[0],
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        cls.initial_brand = Brand.objects.create(user=cls.user1, **cls.brand_data)
        cls.initial_brand.formats.set(cls.formats[:3])  # format 1, 2 and 3
        cls.initial_brand.categories_of_interest.set(cls.categories[1:5])  # category 2, 3, 4, 5
        cls.initial_brand.tags.set(cls.tags[:4])  # tag 1, 2, 3, 4
        cls.initial_brand.goals.set(cls.goals[:3])  # goal 1, 2, 3

        # priority1
        cls.brand1 = Brand.objects.create(
            user=cls.user2,
            **{**cls.brand_data, 'category': cls.categories[1], 'city': cls.city1}
        )
        cls.brand1.formats.set(cls.formats[1:3])  # format 2 and 3
        cls.brand1.tags.set(cls.tags[1:4])  # tag 2, 3, 4
        cls.brand1.goals.set(cls.goals[1:3])  # goal 2, 3

        # priority2
        # subs_count don't match
        cls.brand2 = Brand.objects.create(
            user=cls.user3,
            **{**cls.brand_data, 'category': cls.categories[2], 'subs_count': 20000, 'city': cls.city1}
        )
        cls.brand2.formats.set(cls.formats[1:4])  # format 2, 3, 4
        cls.brand2.tags.set(cls.tags[1:3])  # tag 2, 3
        cls.brand2.goals.set(cls.goals[1:4])  # goal 2, 3, 4

        # priority3
        # subs_count and avg_bill don't match
        cls.brand3 = Brand.objects.create(
            user=cls.user4,
            **{**cls.brand_data, 'category': cls.categories[3], 'subs_count': 20000, 'avg_bill': 20000, 'city': cls.city2}
        )
        cls.brand3.formats.set(cls.formats[2:4])  # format 3, 4
        cls.brand3.tags.set(cls.tags[1:5])  # tag 2, 3, 4, 5
        cls.brand3.goals.set([cls.goals[2]])  # goal 3

        # priority4
        # subs_count, avg_bill and goals don't match
        cls.brand4 = Brand.objects.create(
            user=cls.user5,
            **{**cls.brand_data, 'category': cls.categories[4], 'subs_count': 20000, 'avg_bill': 20000, 'city': cls.city2}
        )
        cls.brand4.formats.set(cls.formats[2:4])  # format 3, 4
        cls.brand4.tags.set(cls.tags[1:5])  # tag 2, 3, 4, 5
        cls.brand4.goals.set(cls.goals[3:5])  # goal 4, 5 # don't match

        # priority5
        # subs_count, avg_bill, goals and tags don't match
        cls.brand5 = Brand.objects.create(
            user=cls.user6,
            **{**cls.brand_data, 'category': cls.categories[1], 'subs_count': 20000, 'avg_bill': 20000, 'city': cls.city2}
        )
        cls.brand5.formats.set(cls.formats[2:4])  # format 3, 4
        cls.brand5.tags.set(cls.tags[5:9])  # tag 6, 7, 8, 9 # don't match
        cls.brand5.goals.set(cls.goals[3:5])  # goal 4, 5 # don't match

        # priority6
        # subs_count, avg_bill, goals, tags and category don't match
        cls.brand6 = Brand.objects.create(
            user=cls.user7,
            **{**cls.brand_data, 'subs_count': 20000, 'avg_bill': 20000, 'city': cls.city3}
        )
        cls.brand6.formats.set(cls.formats[2:4])  # format 3, 4
        cls.brand6.tags.set(cls.tags[5:9])  # tag 6, 7, 8, 9 # don't match
        cls.brand6.goals.set(cls.goals[3:5])  # goal 4, 5 # don't match

        # priority7
        # subs_count, avg_bill, goals, tags, category and formats don't match
        cls.brand7 = Brand.objects.create(
            user=cls.user8,
            **{**cls.brand_data, 'subs_count': 20000, 'avg_bill': 20000, 'city': cls.city3}
        )
        cls.brand7.formats.set([cls.formats[3]])  # format 4 # don't match
        cls.brand7.tags.set(cls.tags[5:9])  # tag 6, 7, 8, 9 # don't match
        cls.brand7.goals.set(cls.goals[3:5])  # goal 4, 5 # don't match

        cls.url = reverse('brand-recommended_brands')

    def test_recommended_brands_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_recommended_brands_wo_brand_not_allowed(self):
        user_wo_brand = User.objects.create_user(
            email='user100@example.com',
            phone='+79993332214',
            fullname='Юзеров Юзер100 Юзерович',
            password='Pass!234',
            is_active=True
        )

        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recommended_brands(self):
        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check number of brands in response
        self.assertEqual(len(response.data['results']), 7)

        # check ordering
        self.assertEqual(response.data['results'][0]['id'], self.brand1.id)
        self.assertEqual(response.data['results'][1]['id'], self.brand2.id)
        self.assertEqual(response.data['results'][2]['id'], self.brand3.id)
        self.assertEqual(response.data['results'][3]['id'], self.brand4.id)
        self.assertEqual(response.data['results'][4]['id'], self.brand5.id)
        self.assertEqual(response.data['results'][5]['id'], self.brand6.id)
        self.assertEqual(response.data['results'][6]['id'], self.brand7.id)

    def test_recommended_brands_exclude_matches(self):
        self.brand_match_1 = Brand.objects.create(
            user=self.user9,
            **self.brand_data
        )

        self.brand_match_2 = Brand.objects.create(
            user=self.user10,
            **self.brand_data
        )

        like_url = reverse('brand-like')

        self.auth_client9.post(like_url, {'target': self.initial_brand.id})
        self.auth_client10.post(like_url, {'target': self.initial_brand.id})
        self.auth_client1.post(like_url, {'target': self.brand_match_1.id})  # initial brand match with brand_match_1
        self.auth_client1.post(like_url, {'target': self.brand_match_2.id})  # initial brand match with brand_match_2

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 7)

    def test_recommended_brands_avg_bill_query_param(self):
        response = self.auth_client1.get(f'{self.url}?avg_bill=20000')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 5)

    def test_recommended_brands_avg_bill_query_param_must_be_positive(self):
        response = self.auth_client1.get(f'{self.url}?avg_bill=-1')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_brands_avg_bill_query_param_must_be_a_number(self):
        response = self.auth_client1.get(f'{self.url}?avg_bill=asd')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_brands_subs_count_query_param(self):
        response = self.auth_client1.get(f'{self.url}?subs_count=20000')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 6)

    def test_recommended_brands_subs_count_query_param_must_be_positive(self):
        response = self.auth_client1.get(f'{self.url}?subs_count=-1')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_brands_subs_count_query_param_must_be_a_number(self):
        response = self.auth_client1.get(f'{self.url}?subs_count=asd')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_brands_category_query_param(self):
        response = self.auth_client1.get(
            f'{self.url}?category={self.categories[1].id}&category={self.categories[2].id}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 3)

    def test_recommended_brands_city_query_param(self):
        response = self.auth_client1.get(f'{self.url}?city={self.city1.id}&city={self.city2.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 5)

    def test_recommended_brands_city_query_param_max_cities(self):
        response = self.auth_client1.get(
            f'{self.url}'
            f'?city={self.city1.id}'
            f'&city={self.city2.id}'
            f'&city={self.city2.id}'
            f'&city={self.city2.id}'
            f'&city={self.city2.id}'
            f'&city={self.city2.id}'
            f'&city={self.city2.id}'
            f'&city={self.city2.id}'
            f'&city={self.city2.id}'
            f'&city={self.city2.id}'
            f'&city={self.city2.id}'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_brands_multiple_query_params(self):
        response = self.auth_client1.get(
            f'{self.url}'
            f'?subs_count=20000'
            f'&avg_bill=20000'
            f'&category={self.categories[1].id}'
            f'&category={self.categories[3].id}'
            f'&city={self.city1.id}'
            f'&city={self.city2.id}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 2)

    def test_number_of_queries(self):
        with self.assertNumQueriesLessThan(15, verbose=True):
            response = self.auth_client1.get(self.url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_recommended_brands_exclude_current_brand(self):
        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(any(brand['id'] == self.initial_brand.id for brand in response.data['results']))
