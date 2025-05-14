from rest_framework import serializers

from core.apps.articles.models import ArticleFile
from core.common.validators import is_valid_file_type


class ArticleFileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleFile
        exclude = ['article']

    def validate_file(self, file):
        ALLOWED_IMAGE_MIME_TYPES = [
            'image/gif', 'image/jpeg', 'image/pjpeg', 'image/png', 'image/webp', 'image/heic', 'image/avif'
        ]

        if not is_valid_file_type(ALLOWED_IMAGE_MIME_TYPES, file):
            raise serializers.ValidationError('Unsupported file type!')

        return file
