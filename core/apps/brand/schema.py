from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema

from core.apps.brand.serializers import (
    MatchSerializer,
    InstantCoopRequestSerializer,
    InstantCoopSerializer, CollaborationSerializer
)


class Fix1(OpenApiViewExtension):
    """
    Описание эндпоинтов
    """
    target_class = 'core.apps.brand.api.BrandViewSet'

    def view_replacement(self):
        @extend_schema(tags=['Brand'])
        class Fixed(self.target_class):
            @extend_schema(
                description='Создать бренд\n\n'
                            'Тип медиа multipart/form-data\n\n'
                            'Объекты и списки (кроме изображений) передавать в виде json строки.\n\n'
                            'Изображения передавать как файлы.\n\n'
                            'Необязательные поля исключать из тела запроса, если они не заполнены.\n\n'
                            'Для категорий, тегов:\n\n'
                            '\tДругое передавать обязательно с "is_other": true\n\n'
                            '\tВ тех, что получили из /api/v1/questionnaire_choices/ '
                            'можно указать "is_other": false, либо не указывать вовсе\n\n'
                            '\tНесуществующие будут проигнорированы при создании, '
                            'НО участвуют в валидации на количество!'
            )
            def create(self, request, *args, **kwargs):
                return super().create(request, *args, **kwargs)

            @extend_schema(description='Получение списка всех брендов')
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

            @extend_schema(description='Получение бренда по id')
            def retrieve(self, request, *args, **kwargs):
                return super().retrieve(request, *args, **kwargs)

            @extend_schema(
                description='Частичное обновление бренда\n\n'
                            'Тип медиа multipart/form-data\n\n'
                            'Объекты и списки (кроме изображений) передавать в виде json строки.\n\n'
                            'Изображения передавать как файлы.\n\n'
                            'Все ключи, значением которых является объект или список (кроме изображений) '
                            '- это новое состояние этого объекта/списка.\n'
                            'Т.е. если хотите добавить что-то к предыдущим значениям, '
                            'то указываете все предыдущие значения + новое. Для удаления то же самое.\n\n'
                            'Для категорий, тегов, форматов, целей:\n\n'
                            '\tДругое передавать обязательно с "is_other": true\n\n'
                            '\tВ тех, что получили из /api/v1/questionnaire_choices/ '
                            'можно указать "is_other": false, либо не указывать вовсе\n\n'
                            '\tНесуществующие будут проигнорированы при создании, '
                            'НО участвуют в валидации на количество!\n\n'
                            'Целевая аудитория:\n\n'
                            '\tМожно указывать ключи верхнего уровня (age, gender, geos, income) в любой комбинации, '
                            'хоть один, хоть все. НО структура их значений строго ограничена! '
                            'Указывать все ключи, которые в них есть. '
                            'Если передать дополнительные ключи, они будут проигнорированы.\n\n'
                            '\tЧтобы удалить значение ключа верхнего уровня нужно передавать:\n\n'
                            '\t - age: {}\n'
                            '\t - gender: {}\n'
                            '\t - geos: []\n'
                            '\t - income: null\n\n'
                            'Изображения, которых может быть несколько, разделены на _add и _remove.\n\n'
                            '\tВ _add передается список изображений, которые надо добавить.\n\n'
                            '\tВ _remove передается список идентификаторов изображений, которые надо удалить.\n\n'
            )
            def partial_update(self, request, *args, **kwargs):
                return super().partial_update(request, *args, **kwargs)

            @extend_schema(description='Удалить бренд')
            def destroy(self, request, *args, **kwargs):
                return super().destroy(request, *args, **kwargs)

            @extend_schema(
                description='Лайкнуть бренд\n\n'
                            'target: id бренда',
                tags=['Brand'],
                responses={201: MatchSerializer}
            )
            def like(self, request, *args, **kwargs):
                return super().like(request, *args, **kwargs)

            @extend_schema(
                tags=['Brand'],
                request=InstantCoopRequestSerializer,
                responses={201: InstantCoopSerializer}
            )
            def instant_coop(self, request, *args, **kwargs):
                return super().instant_coop(request, *args, **kwargs)

            @extend_schema(
                tags=['Brand'],
                responses={201: CollaborationSerializer}
            )
            def report_collab(self, request, *args, **kwargs):
                return super().report_collab(request, *args, **kwargs)

        return Fixed


class Fix2(OpenApiViewExtension):
    target_class = 'core.apps.brand.api.QuestionnaireChoicesListView'

    def view_replacement(self):
        @extend_schema(tags=['Questionnaire'])
        class Fixed(self.target_class):
            """
            Get answer choices for questionnaire choices questions
            """
            pass

        return Fixed
