from django.apps import AppConfig


class BrandConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.apps.brand'

    def ready(self):
        import core.apps.brand.schema
