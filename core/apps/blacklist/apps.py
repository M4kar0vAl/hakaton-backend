from django.apps import AppConfig


class BlacklistConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.apps.blacklist'

    def ready(self):
        import core.apps.blacklist.schema
