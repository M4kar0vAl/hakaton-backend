from django.conf import settings
from rest_framework import serializers

from core.apps.articles.models import ArticleFile, Tutorial, Article, AbstractBaseArticle, CommunityArticle
from core.common.validators import is_valid_file_type


class ArticleFileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleFile
        exclude = ['article']

    def validate_file(self, file):
        if not is_valid_file_type(settings.ALLOWED_IMAGE_MIME_TYPES, file):
            raise serializers.ValidationError('Unsupported file type!')

        return file


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        exclude = ['id']


class BaseArticleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbstractBaseArticle
        exclude = ['body', 'is_published']


class BaseArticleRetrieveSerializer(serializers.ModelSerializer):
    body = ArticleSerializer(read_only=True)

    class Meta:
        model = AbstractBaseArticle
        fields = ['body']


class TutorialListSerializer(BaseArticleListSerializer):
    class Meta(BaseArticleListSerializer.Meta):
        model = Tutorial


class TutorialRetrieveSerializer(BaseArticleRetrieveSerializer):
    class Meta(BaseArticleRetrieveSerializer.Meta):
        model = Tutorial


class CommunityArticleListSerializer(BaseArticleListSerializer):
    class Meta(BaseArticleListSerializer.Meta):
        model = CommunityArticle


class CommunityArticleRetrieveSerializer(BaseArticleRetrieveSerializer):
    class Meta(BaseArticleRetrieveSerializer.Meta):
        model = CommunityArticle
