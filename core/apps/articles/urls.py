from django.urls import path

from core.apps.articles.api import ArticleFileUploadView

urlpatterns = [
    path('tinymce/upload', ArticleFileUploadView.as_view(), name='tinymce_image_upload')
]
