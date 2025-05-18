from bs4 import BeautifulSoup
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.articles.models import Article, ArticleFile


@receiver(post_save, sender=Article, dispatch_uid='attach_uploaded_files_to_article')
def attach_uploaded_files_to_article(instance, created, **kwargs):
    soup = BeautifulSoup(instance.content, 'lxml')
    # get sources of all images in article content
    new_images_srcs = [img.get('src').removeprefix(settings.MEDIA_URL) for img in soup.find_all('img')]

    if created:
        # attach all images to an article
        ArticleFile.objects.filter(file__in=new_images_srcs).update(article=instance)
    else:
        current_images_srcs = list(ArticleFile.objects.filter(article=instance).values_list('file', flat=True))

        # find sources which are in received html, but not in current attached images
        to_update = [src for src in new_images_srcs if src not in current_images_srcs]  # sources of images to attach

        # find sources which are currently attached, but not in received html
        to_delete = [src for src in current_images_srcs if src not in new_images_srcs]  # sources of images to delete

        if to_delete:
            ArticleFile.objects.filter(file__in=to_delete).delete()

        if to_update:
            ArticleFile.objects.filter(file__in=to_update).update(article=instance)
