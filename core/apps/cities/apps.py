from django.apps import AppConfig


class CitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.apps.cities'

    def ready(self):
        import core.apps.cities.schema
