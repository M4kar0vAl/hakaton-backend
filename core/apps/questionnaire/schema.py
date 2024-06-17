from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema

from core.apps.accounts import serializers


class Fix1(OpenApiViewExtension):
    """
    Описание эндпоинтов
    """
    target_class = 'core.apps.questionnaire.api.QuestionViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Questionnaire'])
        class Fixed(self.target_class):
            @extend_schema(
                description='Получить анкету\n\n'
                            'text: Вопрос\n\n'
                            'answer_type: Тип ответа на вопрос. Может быть:\n\n'
                            '::TEXT: строка;\n\n'
                            '::ONE: выбор с одним вариантом;\n\n'
                            '::MANY: множественный выбор;\n\n'
                            '::IMAGE: загрузка изображения.\n\n'
                            'choices: список с вариантами ответа'
            )
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

        return Fixed
