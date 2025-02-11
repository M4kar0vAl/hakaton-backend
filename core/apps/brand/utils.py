from collections import Counter
from datetime import datetime
from typing import Any, Generator

from dateutil.relativedelta import relativedelta
from django.db.models import Q, Value, QuerySet, Prefetch, Count
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework import serializers

from core.apps.brand.models import Match, Collaboration, Brand, ProductPhoto
from core.apps.brand.pagination import StandardResultsSetPagination


def get_file_extension(filename):
    """
    Get extension of a file in .ext format
    """
    return '.' + filename.split('.')[-1]


def get_schema_standard_pagination_parameters() -> list[OpenApiParameter]:
    """
    Get standard pagination query parameters for use in OpenAPI schema generation.
    """
    standard_pagination_class = StandardResultsSetPagination

    return [
        OpenApiParameter(
            'page',
            OpenApiTypes.INT,
            OpenApiParameter.QUERY,
            description='Page number.\n\n'
                        'To get next or previous page use "next" and "previous" links from the response.'
                        '\n\n'
                        f'To get last page pass "{standard_pagination_class.last_page_strings[0]}" as a value.'
        ),
        OpenApiParameter(
            standard_pagination_class.page_size_query_param,
            OpenApiTypes.INT,
            OpenApiParameter.QUERY,
            description='Number of objects per page.\n\n'
                        f'\tdefault: {standard_pagination_class.page_size}\n\n'
                        '\tmin: 1\n\n'
                        f'\tmax: {standard_pagination_class.max_page_size}'
        )
    ]


def get_periods(number_of_months: int) -> list[tuple[datetime, datetime]]:
    """
    Convert number of months to periods, which can be used as __range lookup input

    The step is 1 month.

    Args:
        number_of_months: the number of months to break into periods

    Returns:
        List of tuples of datetime objects.
    """
    result = []
    now = timezone.now()

    for i in range(number_of_months):
        result.append((now - relativedelta(months=1 + i), now - relativedelta(months=i)))

    return result


def period_to_str(period: tuple[datetime, datetime]) -> str:
    """
    Returns a string representation of given period.

    String representation is: YYYY-MM-DD HH:mm:ss.ms - YYYY-MM-DD HH:mm:ss.ms
    """
    return ' - '.join(map(str, period))


def generate_queries_for_likes(periods: list[tuple[datetime, datetime]], brand: Brand) -> QuerySet[str]:
    """
    Generate query for each period

    Returns a queryset that will return a list of string representations of periods.
    Each period appears a number of times equal to the number of likes during this period.

    For example:
        Queryset[period1, period1, period1, period2, period2]
        This queryset means that there were 3 likes during period1 and 2 likes during period2
    """
    for period in periods:
        period_as_str = period_to_str(period)

        # is_match=False MUST NOT be specified in filters,
        # because we want to count EVERY like, including those which led to match
        likes_for_period = Match.objects.filter(
            initiator=brand, like_at__range=period
        ).annotate(period=Value(period_as_str)).values_list('period', flat=True)

        yield likes_for_period


def generate_queries_for_matches(periods: list[tuple[datetime, datetime]], brand: Brand) -> QuerySet[str]:
    """
    Generate query for each period

    Returns a queryset that will return a list of string representations of periods.
    Each period appears a number of times equal to the number of matches during this period.

    For example:
        Queryset[period1, period1, period1, period2, period2]
        This queryset means that there were 3 matches during period1 and 2 matches during period2
    """
    for period in periods:
        period_as_str = period_to_str(period)

        matches_for_period = Match.objects.filter(
            Q(initiator=brand) | Q(target=brand), is_match=True, match_at__range=period
        ).annotate(period=Value(period_as_str)).values_list('period', flat=True)

        yield matches_for_period


def generate_queries_for_collabs(periods: list[tuple[datetime, datetime]], brand: Brand) -> QuerySet[str]:
    """
    Generate query for each period

    Returns a queryset that will return a list of string representations of periods.
    Each period appears a number of times equal to the number of collabs during this period.

    For example:
        Queryset[period1, period1, period1, period2, period2]
        This queryset means that there were 3 collabs during period1 and 2 collabs during period2
    """
    for period in periods:
        period_as_str = period_to_str(period)

        # there can be up to 2 collabs pointing at the same match
        # to count collabs correctly, we must count only distinct ones.
        # That's why we use distinct on "match" field
        # WARNING distinct on specified fields works only on postgresql db backend
        collabs_for_period = Collaboration.objects.filter(
            Q(reporter=brand) | Q(collab_with=brand), created_at__range=period
        ).order_by('match_id').distinct('match_id').annotate(
            period=Value(period_as_str)
        ).values_list('period', flat=True)

        yield collabs_for_period


def get_statistics_list(brand: Brand, period: int) -> list[dict[str, Any]]:
    """
    Get a list of current brand statistics for period

    Args:
        brand: a brand instance for which to calculate statistics
        period: number of months (statistics will be calculated from {now - period} to {now})

    Returns:
        A list of dicts to use in the serializer of the following structure
        [{
            'period': 'period_as_str',
            'likes': 1,
            'matches': 1,
            'collabs': 1
        }]
    """
    periods = get_periods(period)

    # generate queries for each period
    likes_queries_gen = generate_queries_for_likes(periods, brand)
    matches_queries_gen = generate_queries_for_matches(periods, brand)
    collabs_queries_gen = generate_queries_for_collabs(periods, brand)

    # get first query for each of like/match/collab
    first_like_query = next(likes_queries_gen)
    first_matches_query = next(matches_queries_gen)
    first_collabs_query = next(collabs_queries_gen)

    # construct the final query for each of like/match/collab
    # final query is a union of all queries for each period
    likes_query_final = first_like_query.union(*[q for q in likes_queries_gen])
    matches_query_final = first_matches_query.union(*[q for q in matches_queries_gen])
    collabs_query_final = first_collabs_query.union(*[q for q in collabs_queries_gen])

    # count number of period occurrences for each like/match/collab
    # each variable will be a dict where key - string representation of the period and value - number of occurrences
    likes_count_for_periods = dict(Counter(likes_query_final).most_common())
    matches_count_for_periods = dict(Counter(matches_query_final).most_common())
    collabs_count_for_periods = dict(Counter(collabs_query_final).most_common())

    results = []

    # construct the resulting list
    for period in periods:
        period_as_str = period_to_str(period)

        results.append({
            'period': period_as_str,
            'likes': likes_count_for_periods.get(period_as_str, 0),
            'matches': matches_count_for_periods.get(period_as_str, 0),
            'collabs': collabs_count_for_periods.get(period_as_str, 0)
        })

    return results


def get_recommended_brands_filter_kwargs(
        avg_bill: int | None,
        subs_count: int | None,
        categories_ids: list[int] | None,
        cities_ids: list[int] | None
) -> dict[str, Any]:
    """
    Validate and transform filter values selected by user into a dictionary.

    Args:
        avg_bill: "average bill" filter value
        subs_count: "subscribers count" filter value
        categories_ids: "categories ids" filter value
        cities_ids: "cities ids" filter value

    Returns:
        Dictionary where the key is a django lookup for the filter and the value is the lookup value
    """
    filter_kwargs = {}

    if avg_bill is not None:
        try:
            avg_bill = int(avg_bill)
        except ValueError:
            raise serializers.ValidationError('"avg_bill" must be a number')

        if avg_bill < 0:
            raise serializers.ValidationError('"avg_bill" cannot be negative')

        filter_kwargs['avg_bill'] = avg_bill

    if subs_count is not None:
        try:
            subs_count = int(subs_count)
        except ValueError:
            raise serializers.ValidationError('"subs_count" must be a number')

        if subs_count < 0:
            raise serializers.ValidationError('"subs_count" cannot be negative')

        filter_kwargs['subs_count'] = subs_count

    if categories_ids:
        filter_kwargs['category__in'] = categories_ids

    if cities_ids:
        max_cities_allowed = 10

        if len(cities_ids) > max_cities_allowed:
            raise serializers.ValidationError(f'You cannot specify more than {max_cities_allowed} cities.')

        filter_kwargs['city__in'] = cities_ids

    return filter_kwargs


def get_recommended_brands_initial_brands(current_brand: Brand, filter_kwargs: dict[str, Any]) -> QuerySet[Brand]:
    """
    Get initial brands queryset.

    Args:
        current_brand: brand for which to get recommended brands
        filter_kwargs: initial filters selected by user

    Returns:
        A queryset of brands that satisfy the filters
    """
    # get ids of current brand likes including matches
    # liked brands as initiator
    # matched brands as initiator
    current_brand_likes_including_matches = current_brand.initiator.values_list('target', flat=True)

    # get ids of brands that have match with current brand as target
    # matched brands as target
    current_brand_matches_ids_as_target = current_brand.target.filter(
        is_match=True
    ).values_list('initiator', flat=True)

    likes_and_matches_ids = list(current_brand_likes_including_matches.union(current_brand_matches_ids_as_target))

    # get all brands that current brand added to its blacklist
    blocked_brands = current_brand.blacklist_as_initiator.values_list('blocked', flat=True)

    # get all brands that added the current one to the blacklist
    blocked_by = current_brand.blacklist_as_blocked.values_list('initiator', flat=True)

    blacklist = list(blocked_brands.union(blocked_by))

    initial_brands = Brand.objects.filter(
        user__isnull=False, **filter_kwargs
    ).exclude(
        # filter out all brands that:
        # - already have match with current one
        # - are in current brand's blacklist
        # - blocked current brand
        pk__in=likes_and_matches_ids + blacklist
    )

    return initial_brands


def get_priority_kwargs(current_brand: Brand) -> dict[int, dict[str, Any]]:
    """
    Get filters for each priority.

    Args:
        current_brand: brand for which to get recommended brands

    Returns:
        Dictionary where the key is a priority (1-indexed) and the value is a dictionary of filters
    """
    # get ids of current brand m2m and instantly evaluate it to avoid unnecessary subqueries
    current_brand_tags = list(current_brand.tags.values_list('id', flat=True))
    current_brand_formats = list(current_brand.formats.values_list('id', flat=True))
    current_brand_goals = list(current_brand.goals.values_list('id', flat=True))
    current_brand_categories_of_interest = list(
        current_brand.categories_of_interest.values_list('id', flat=True)
    )

    priority_1_kwargs = {
        'formats__in': current_brand_formats,
        'category__in': current_brand_categories_of_interest,
        'tags__in': current_brand_tags,
        'goals__in': current_brand_goals,
        'avg_bill': current_brand.avg_bill,
        'subs_count': current_brand.subs_count
    }

    priorities = {}

    for priority in range(1, len(priority_1_kwargs) + 2):
        priorities[priority] = {**priority_1_kwargs}  # MUST make a copy

        try:
            priority_1_kwargs.popitem()
        except KeyError:
            pass

    return priorities


def generate_recommended_brands_queries(
        current_brand: Brand,
        initial_brands: QuerySet[Brand],
        priority_kwargs: dict[int, dict[str, Any]]
) -> Generator[QuerySet[Brand], None, None]:
    """
    Generate a query for each priority in priority_kwargs

    Args:
        current_brand: brand for which to get recommended brands
        initial_brands: queryset to get initial brands,
                        which is used as a starting point for calculating recommended brands
        priority_kwargs: priority - filters mapping for each priority

    Returns: generator that yields queries to get recommended brands for each of the priorities
    """
    last_priority_num = len(priority_kwargs)
    cur_exclude_set = {current_brand.pk}

    for priority, kwargs in priority_kwargs.items():
        cur_lookups_set = set(kwargs.keys())

        cur_query = initial_brands.filter(
            **kwargs
        ).distinct().exclude(
            pk__in=cur_exclude_set
        ).select_related(
            'city',
            'category'
        ).prefetch_related(
            Prefetch(
                'product_photos',
                queryset=ProductPhoto.objects.filter(format=ProductPhoto.MATCH),
                to_attr='match_photos'
            )
        ).annotate(
            priority=Value(priority),
            formats_matches_num=Count('formats') if 'formats__in' in cur_lookups_set else Value(0),
            tags_matches_num=Count('tags') if 'tags__in' in cur_lookups_set else Value(0),
            goals_matches_num=Count('goals') if 'goals__in' in cur_lookups_set else Value(0),
        )

        if priority != last_priority_num:
            # no need to update the exclude set with the last priority
            cur_exclude = set(initial_brands.filter(
                **kwargs
            ).distinct().exclude(
                pk__in=cur_exclude_set
            ).values_list('id', flat=True))

            cur_exclude_set.update(cur_exclude)

        yield cur_query


def get_recommended_brands(
        current_brand: Brand,
        avg_bill: int | None,
        subs_count: int | None,
        categories_ids: list[int] | None,
        cities_ids: list[int] | None
) -> QuerySet[Brand]:
    """
    Get recommended brands for the current brand.

    Args:
        current_brand: brand for which to get recommended brands
        avg_bill: "average bill" filter value
        subs_count: "subscribers count" filter value
        categories_ids: "categories ids" filter value
        cities_ids: "cities ids" filter value

    Returns:
        Recommended brands queryset
    """
    filter_kwargs = get_recommended_brands_filter_kwargs(avg_bill, subs_count, categories_ids, cities_ids)
    initial_brands = get_recommended_brands_initial_brands(current_brand, filter_kwargs)
    priority_kwargs = get_priority_kwargs(current_brand)

    queries_gen = generate_recommended_brands_queries(current_brand, initial_brands, priority_kwargs)

    return next(queries_gen).union(*queries_gen).order_by(
        'priority', '-formats_matches_num', '-tags_matches_num', '-goals_matches_num'
    )
