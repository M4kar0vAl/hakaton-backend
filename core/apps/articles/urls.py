from django.urls import path
from rest_framework import routers

from core.apps.articles.api import (
    ArticleFileUploadView,
    TutorialViewSet,
    CommunityArticleViewSet,
    MediaArticleViewSet,
    NewsArticleViewSet
)

router = routers.DefaultRouter()
router.register('tutorials', TutorialViewSet, basename='tutorials')
router.register('community_articles', CommunityArticleViewSet, basename='community_articles')
router.register('media_articles', MediaArticleViewSet, basename='media_articles')
router.register('news_articles', NewsArticleViewSet, basename='news_articles')

urlpatterns = [
    path('tinymce/upload', ArticleFileUploadView.as_view(), name='tinymce_image_upload')
]

urlpatterns += router.urls
