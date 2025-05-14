import os
import uuid

from django.db import models
from tinymce.models import HTMLField

from core.apps.brand.utils import get_file_extension


def article_file_upload_path(instance, filename):
    extension = get_file_extension(filename)
    new_filename = f'{uuid.uuid4()}{extension}'

    return os.path.join('articles', new_filename)


class Article(models.Model):
    content = HTMLField(verbose_name='Контент')

    def __str__(self):
        return f'Article {self.pk}'

    def __repr__(self):
        return f'{self.__class__.__name__} {self.pk}'


class ArticleFile(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, null=True, related_name='files', verbose_name='Статья'
    )
    file = models.FileField(upload_to=article_file_upload_path, verbose_name='Файл')

    def __str__(self):
        return f'Article File {self.pk}'

    def __repr__(self):
        return f'{self.__class__.__name__} {self.pk}'
