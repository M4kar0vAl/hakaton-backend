from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.apps.accounts'

    def ready(self):
        import core.apps.accounts.schema
