from rest_framework import serializers


def get_file_extension(filename):
    """
    Get extension of a file in .ext format
    """
    return '.' + filename.split('.')[-1]


def get_paginated_response_serializer(
        serializer: type[serializers.Serializer] | type[serializers.ModelSerializer]
) -> type[serializers.Serializer]:
    """
    Decorator that should be used with serializers as response serializer in drf-spectacular schema.

    Returns:
        Serializer class that has pagination attributes.
    """

    class PaginatedSerializer(serializers.Serializer):
        count = serializers.IntegerField(required=True)
        next = serializers.URLField()
        previous = serializers.URLField()
        results = serializer(many=True, required=True)

    return PaginatedSerializer
