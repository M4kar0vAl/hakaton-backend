from collections import Counter
from datetime import datetime
from typing import Any

from dateutil.relativedelta import relativedelta
from django.db.models import Q, Value, QuerySet
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from core.apps.brand.models import Match, Collaboration, Brand
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
