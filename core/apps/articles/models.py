import os
import uuid

from django.db import models
from tinymce.models import HTMLField

from core.common.utils import get_file_extension


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


class Tutorial(models.Model):
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    excerpt = models.CharField(max_length=255, verbose_name='Выдержка')
    preview_video = models.FileField(upload_to='tutorials/preview_videos/', verbose_name='Превью видео')
    body = models.OneToOneField(to=Article, on_delete=models.CASCADE, verbose_name='Контент')

    def __str__(self):
        return f'Tutorial: {self.title}'

    def __repr__(self):
        return f'{self.__class__.__name__} {self.pk}'
