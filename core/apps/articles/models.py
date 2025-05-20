import os

from django.db import models
from tinymce.models import HTMLField

from core.common.utils import get_random_filename_with_extension
from core.common.validators import is_valid_video, is_valid_image


def article_file_upload_path(instance, filename):
    new_filename = get_random_filename_with_extension(filename)

    return os.path.join('articles', new_filename)


def article_preview_upload_path(instance, filename):
    new_filename = get_random_filename_with_extension(filename)

    match instance:
        case CommunityArticle():
            subfolder = 'community_articles'
        case Tutorial():
            subfolder = 'tutorials'
        case _:
            subfolder = ''

    return os.path.join('articles', 'previews', subfolder, new_filename)


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


class AbstractBaseArticle(models.Model):
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    excerpt = models.CharField(max_length=255, verbose_name='Выдержка')
    preview = models.ImageField(
        upload_to=article_preview_upload_path, validators=[is_valid_image], verbose_name='Превью'
    )
    body = models.OneToOneField(to=Article, on_delete=models.CASCADE, verbose_name='Контент')
    is_published = models.BooleanField(default=False, verbose_name='Опубликовано')

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.__class__.__name__}: {self.title}'

    def __repr__(self):
        return f'{self.__class__.__name__} {self.pk}'


class Tutorial(AbstractBaseArticle):
    preview = models.FileField(
        upload_to=article_preview_upload_path, validators=[is_valid_video], verbose_name='Превью видео'
    )


class CommunityArticle(AbstractBaseArticle):
    class Meta:
        verbose_name = 'Community Article'
        verbose_name_plural = 'Community Articles'
