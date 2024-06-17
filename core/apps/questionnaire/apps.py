from django.apps import AppConfig


class QuestionnaireConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.apps.questionnaire'

    def ready(self):
        import core.apps.questionnaire.schema
