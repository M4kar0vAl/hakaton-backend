import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.blacklist.factories import BlackListFactory
from core.apps.brand.factories import (
    BrandShortFactory,
    TagFactory,
    FormatFactory,
    GoalFactory,
    CategoryFactory,
    MatchFactory
)
from core.apps.cities.factories import CityFactory
from tests.mixins import AssertNumQueriesLessThanMixin


class BrandRecommendedBrandsTestCase(
    APITestCase,
    AssertNumQueriesLessThanMixin
):
    @classmethod
    def setUpTestData(cls):
        users = UserFactory.create_batch(8)

        for i, user in enumerate(users, start=1):
            # set users to class attributes named user{i}
            setattr(cls, f'user{i}', user)

            # create APIClient instance for each user
            setattr(cls, f'auth_client{i}', APIClient())

            # force authenticate clients
            getattr(cls, f'auth_client{i}').force_authenticate(user)

        cls.city1, cls.city2, cls.city3 = CityFactory.create_batch(3)

        cls.initial_tags = TagFactory.create_batch(3)
        cls.initial_formats = FormatFactory.create_batch(3)
        cls.initial_goals = GoalFactory.create_batch(3)
        cls.initial_categories_of_interest = CategoryFactory.create_batch(3)

        cls.initial_brand = BrandShortFactory(
            user=cls.user1,
            tags=cls.initial_tags,
            formats=cls.initial_formats,
            goals=cls.initial_goals,
            categories_of_interest=cls.initial_categories_of_interest,
            has_sub=True
        )

        cls.initial_subs_count = cls.initial_brand.subs_count
        cls.initial_avg_bill = cls.initial_brand.avg_bill

        # priority1
        # everything matches
        cls.brand1 = BrandShortFactory(
            user=cls.user2,
            category=factory.Iterator(cls.initial_categories_of_interest),
            tags=cls.initial_tags[:2],
            formats=cls.initial_formats[:2],
            goals=cls.initial_goals[:2],
            subs_count=cls.initial_subs_count,
            avg_bill=cls.initial_avg_bill,
        )

        # priority2
        # subs_count don't match
        cls.brand2 = BrandShortFactory(
            user=cls.user3,
            category=factory.Iterator(cls.initial_categories_of_interest),
            tags=[*cls.initial_tags, TagFactory()],
            formats=[*cls.initial_formats, FormatFactory()],
            goals=[*cls.initial_goals, GoalFactory()],
            avg_bill=cls.initial_avg_bill,
        )

        # priority3
        # subs_count and avg_bill don't match
        cls.brand3 = BrandShortFactory(
            user=cls.user4,
            category=factory.Iterator(cls.initial_categories_of_interest),
            tags=cls.initial_tags[:2],
            formats=cls.initial_formats[:2],
            goals=cls.initial_goals[:2],
        )

        # priority4
        # subs_count, avg_bill and goals don't match
        cls.brand4 = BrandShortFactory(
            user=cls.user5,
            category=factory.Iterator(cls.initial_categories_of_interest),
            tags=cls.initial_tags[:2],
            formats=cls.initial_formats[:2],
            goals=GoalFactory.create_batch(3),
        )

        # priority5
        # subs_count, avg_bill, goals and tags don't match
        cls.brand5 = BrandShortFactory(
            user=cls.user6,
            category=factory.Iterator(cls.initial_categories_of_interest),
            tags=TagFactory.create_batch(3),
            formats=cls.initial_formats[:2],
            goals=GoalFactory.create_batch(3),
        )

        # priority6
        # subs_count, avg_bill, goals, tags and category don't match
        cls.brand6 = BrandShortFactory(
            user=cls.user7,
            category=CategoryFactory(),
            tags=TagFactory.create_batch(3),
            formats=cls.initial_formats[:2],
            goals=GoalFactory.create_batch(3),
        )

        # priority7
        # subs_count, avg_bill, goals, tags, category and formats don't match
        cls.brand7 = BrandShortFactory(
            user=cls.user8,
            category=CategoryFactory(),
            tags=TagFactory.create_batch(3),
            formats=FormatFactory.create_batch(3),
            goals=GoalFactory.create_batch(3),
        )

        cls.recommended_brands = [getattr(cls, f'brand{i}') for i in range(1, 8)]
        cls.recommended_brands_num = len(cls.recommended_brands)
        cls.brands_with_initial_avg_bill_num = len(
            list(filter(lambda brand: brand.avg_bill == cls.initial_avg_bill, cls.recommended_brands))
        )
        cls.brands_with_initial_subs_count_num = len(
            list(filter(lambda brand: brand.subs_count == cls.initial_subs_count, cls.recommended_brands))
        )
        cls.brands_that_interest_initial_one_num = len(list(filter(
            lambda brand: brand.category in cls.initial_categories_of_interest, cls.recommended_brands
        )))

        cls.url = reverse('brand-recommended_brands')

    def test_recommended_brands_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_recommended_brands_wo_brand_not_allowed(self):
        user_wo_brand = UserFactory()
        auth_client_wo_brand = APIClient()
        auth_client_wo_brand.force_authenticate(user_wo_brand)

        response = auth_client_wo_brand.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recommended_brands_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recommended_brands(self):
        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check number of brands in response
        self.assertEqual(len(response.data['results']), self.recommended_brands_num)

        # check ordering
        self.assertEqual(response.data['results'][0]['id'], self.brand1.id)
        self.assertEqual(response.data['results'][1]['id'], self.brand2.id)
        self.assertEqual(response.data['results'][2]['id'], self.brand3.id)
        self.assertEqual(response.data['results'][3]['id'], self.brand4.id)
        self.assertEqual(response.data['results'][4]['id'], self.brand5.id)
        self.assertEqual(response.data['results'][5]['id'], self.brand6.id)
        self.assertEqual(response.data['results'][6]['id'], self.brand7.id)

    def test_recommended_brands_exclude_likes(self):
        MatchFactory(like=True, initiator=self.initial_brand, target=self.brand1)  # initial brand likes brand1
        MatchFactory(like=True, initiator=self.brand2, target=self.initial_brand)  # brand2 likes initial brand

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        # results must exclude likes of the current brand and must not exclude brands that liked the current one
        self.assertEqual(len(results), self.recommended_brands_num - 1)

    def test_recommended_brands_exclude_matches(self):
        # initial brand match with brand1 and brand2
        MatchFactory.create_batch(
            2, initiator=self.initial_brand, target=factory.Iterator([self.brand1, self.brand2])
        )

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), self.recommended_brands_num - 2)

    def test_recommended_brands_avg_bill_query_param(self):
        response = self.auth_client1.get(f'{self.url}?avg_bill={self.initial_avg_bill}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), self.brands_with_initial_avg_bill_num)

    def test_recommended_brands_avg_bill_query_param_must_be_positive(self):
        response = self.auth_client1.get(f'{self.url}?avg_bill=-1')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_brands_avg_bill_query_param_must_be_a_number(self):
        response = self.auth_client1.get(f'{self.url}?avg_bill=asd')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_brands_subs_count_query_param(self):
        response = self.auth_client1.get(f'{self.url}?subs_count={self.initial_subs_count}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), self.brands_with_initial_subs_count_num)

    def test_recommended_brands_subs_count_query_param_must_be_positive(self):
        response = self.auth_client1.get(f'{self.url}?subs_count=-1')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_brands_subs_count_query_param_must_be_a_number(self):
        response = self.auth_client1.get(f'{self.url}?subs_count=asd')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_brands_category_query_param(self):
        url = (
            f'{self.url}?'
            f'{"&".join([f"category={c.pk}" for c in self.initial_categories_of_interest])}'
        )
        response = self.auth_client1.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), self.brands_that_interest_initial_one_num)

    def test_recommended_brands_city_query_param(self):
        response = self.auth_client1.get(f'{self.url}?city={self.brand1.city_id}&city={self.brand2.city_id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_recommended_brands_city_query_param_max_cities(self):
        url = (
            f'{self.url}?'
            f'{"&".join([f"city={self.brand1.city_id}" for _ in range(11)])}'
        )
        response = self.auth_client1.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_brands_multiple_query_params(self):
        url = (
            f'{self.url}'
            f'?subs_count={self.initial_subs_count}'
            f'&avg_bill={self.initial_avg_bill}'
            f'&{"&".join([f"category={c.pk}" for c in self.initial_categories_of_interest])}'
            f'&city={self.brand1.city_id}'
            f'&city={self.brand2.city_id}'
        )
        response = self.auth_client1.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data['results']),
            min(
                self.brands_with_initial_subs_count_num,
                self.brands_with_initial_avg_bill_num,
                self.brands_that_interest_initial_one_num,
                2
            )
        )

    def test_number_of_queries(self):
        with self.assertNumQueriesLessThan(16, verbose=True):
            response = self.auth_client1.get(self.url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_recommended_brands_exclude_current_brand(self):
        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(any(brand['id'] == self.initial_brand.id for brand in response.data['results']))

    def test_recommended_brands_exclude_blacklist(self):
        BlackListFactory(initiator=self.initial_brand, blocked=self.brand1)  # initial brand blocks brand1
        BlackListFactory(initiator=self.brand2, blocked=self.initial_brand)  # brand2 blocks initial brand

        response = self.auth_client1.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        # results must exclude both blocked brands and brands that blocked the current one
        self.assertEqual(len(results), self.recommended_brands_num - 2)
