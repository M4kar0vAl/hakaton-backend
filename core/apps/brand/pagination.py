from django.core.paginator import Paginator
from django.utils.functional import cached_property
from rest_framework.pagination import PageNumberPagination


class FasterDjangoPaginator(Paginator):
    # doesn't execute counting query
    @cached_property
    def count(self):
        return len(self.object_list)


class StandardResultsSetPagination(PageNumberPagination):
    django_paginator_class = FasterDjangoPaginator
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000
