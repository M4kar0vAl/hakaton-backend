from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema

from core.apps.accounts import serializers


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
                            'Тип медиа application/json\n\n'
                            'Вложенные объекты (с вариантами ответов):\n\n'
                            '::text: Текст ответа, в точности как в вариантах ответа на вопрос.'
                            ' Если вариант "Свой вариант", должен быть передан как '
                            '{"text": "Свой вариант: мой вариант ответа"} '
                            '(с пробелом после двоеточия)\n\n'
                            '::question: id вопроса, на который отправляется ответ.\n\n'
                            'Изображения передавать в виде строки base64'
            )
            def create(self, request, *args, **kwargs):
                return super().create(request, *args, **kwargs)

            @extend_schema(description='Получение списка всех брендов')
            def list(self, request, *args, **kwargs):
                return super().list(request, *args, **kwargs)

            @extend_schema(description='Получение бренда по id')
            def retrieve(self, request, *args, **kwargs):
                return super().retrieve(request, *args, **kwargs)

            @extend_schema(description='Полное обновление бренда')
            def update(self, request, *args, **kwargs):
                return super().update(request, *args, **kwargs)

            @extend_schema(description='Частичное обновление бренда')
            def partial_update(self, request, *args, **kwargs):
                return super().partial_update(request, *args, **kwargs)

            @extend_schema(description='Удалить бренд')
            def destroy(self, request, *args, **kwargs):
                return super().destroy(request, *args, **kwargs)

        return Fixed
