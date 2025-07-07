from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.brand.factories import CategoryFactory, TagFactory, FormatFactory, GoalFactory
from core.apps.brand.models import Category, Tag, Format, Goal
from tests.mixins import AssertNumQueriesLessThanMixin


class QuestionnaireChoicesListTestCase(APITestCase, AssertNumQueriesLessThanMixin):
    @classmethod
    def setUpTestData(cls):
        return_categories_count = Category.objects.filter(is_other=False).count()
        return_tags_count = Tag.objects.filter(is_other=False).count()
        return_formats_count = Format.objects.filter(is_other=False).count()
        return_goals_count = Goal.objects.filter(is_other=False).count()

        cls.returning_count = {
            'categories': return_categories_count,
            'tags': return_tags_count,
            'formats': return_formats_count,
            'goals': return_goals_count
        }

        cls.url = reverse('questionnaire_choices')

    def test_questionnaire_choices_list(self):
        # check the number of queries
        with self.assertNumQueriesLessThan(5, verbose=True):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for key, count in self.returning_count.items():
            self.assertTrue(key in response.data)
            self.assertEqual(len(response.data[key]), count)

    def test_questionnaire_choices_list_exclude_other(self):
        CategoryFactory(is_other=True)
        TagFactory(is_other=True)
        FormatFactory(is_other=True)
        GoalFactory(is_other=True)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for key, count in self.returning_count.items():
            self.assertTrue(key in response.data)
            self.assertEqual(len(response.data[key]), count)
