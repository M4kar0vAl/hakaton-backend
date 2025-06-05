from random import randint

import factory
from factory.django import DjangoModelFactory

from core.apps.articles.models import Article, ArticleFile, Tutorial, CommunityArticle, MediaArticle, NewsArticle


class ArticleFileFactory(DjangoModelFactory):
    class Meta:
        model = ArticleFile

    article = None
    file = factory.django.ImageField()


class ArticleFactory(DjangoModelFactory):
    class Meta:
        model = Article

    content = factory.Faker('paragraph', nb_sentences=10)


class ArticleWithFilesFactory(ArticleFactory):
    files = factory.RelatedFactoryList(ArticleFileFactory, factory_related_name='file', size=lambda: randint(1, 3))


class AbstractBaseArticleFactory(DjangoModelFactory):
    class Meta:
        abstract = True

    class Params:
        has_preview = False

    title = factory.Sequence(lambda n: f'Article {n}')
    excerpt = factory.Faker('paragraph')
    preview = factory.Maybe(
        'has_preview',
        yes_declaration=factory.django.ImageField(),
        no_declaration=''
    )
    body = factory.SubFactory(ArticleFactory)
    is_published = True


class TutorialFactory(AbstractBaseArticleFactory):
    class Meta:
        model = Tutorial

    title = factory.Sequence(lambda n: f'Tutorial {n}')
    preview = factory.Maybe(
        'has_preview',
        yes_declaration=factory.django.FileField(),
        no_declaration=''
    )


class CommunityArticleFactory(AbstractBaseArticleFactory):
    class Meta:
        model = CommunityArticle

    title = factory.Sequence(lambda n: f'Community Article {n}')


class MediaArticleFactory(AbstractBaseArticleFactory):
    class Meta:
        model = MediaArticle

    title = factory.Sequence(lambda n: f'Media Article {n}')


class NewsArticleFactory(AbstractBaseArticleFactory):
    class Meta:
        model = NewsArticle

    title = factory.Sequence(lambda n: f'News Article {n}')
