from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

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
