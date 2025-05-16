from django.urls import path
from rest_framework import routers

from core.apps.articles.api import ArticleFileUploadView, TutorialViewSet

router = routers.DefaultRouter()
router.register('tutorials', TutorialViewSet, basename='tutorials')

urlpatterns = [
    path('tinymce/upload', ArticleFileUploadView.as_view(), name='tinymce_image_upload')
]

urlpatterns += router.urls
