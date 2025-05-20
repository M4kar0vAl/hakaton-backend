from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.apps.articles'

    def ready(self):
        import core.apps.articles.schema
        from . import signals
