from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from core.apps.brand.serializers import (
    MatchSerializer,
    InstantCoopSerializer,
    LikedBySerializer,
    BrandCreateResponseSerializer,
    RecommendedBrandsSerializer,
    MyLikesSerializer,
    MyMatchesSerializer, StatisticsSerializer
)
from core.apps.brand.utils import get_schema_standard_pagination_parameters


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
                            'НО участвуют в валидации на количество!',
                responses={201: BrandCreateResponseSerializer}
            )
            def create(self, request, *args, **kwargs):
                return super().create(request, *args, **kwargs)

            @extend_schema(
                description='Get brand by id.\n\n'
                            'Brand cannot get information about itself using this method.\n\n'
                            'To get info about yourself use GET brand/me endpoint.\n\n'
                            'Authenticated brand with active subscription only.'
            )
            def retrieve(self, request, *args, **kwargs):
                return super().retrieve(request, *args, **kwargs)

            @extend_schema(
                description='Like a brand\n\n'
                            '\ttarget: brand id\n\n'
                            'Situations and outcomes:\n\n'
                            '\t1) brand1 "like" brand2 -> like (is_match: false, room: null)\n\n'
                            '\t2) brand1 "like" brand2 & brand2 "like" brand1 '
                            '-> match (is_match: true, room: 1 (room type is MATCH))\n\n'
                            '\t3) brand1 "like" brand2 & brand1 "instant coop" brand2 '
                            '-> like + 1 message (is_match: false, room: 1 (room type is INSTANT))\n\n'
                            '\t4) brand1 "like" brand2 & brand1 "instant coop" brand2 & brand2 "like" brand1 '
                            '-> like + 1 message (is_match: false, room: 1 (room type is INSTANT)) '
                            '-> match (is_match: true, room: 1 (room type is MATCH, id did not change))\n\n'
                            'Authenticated brand with active subscription only',
                tags=['Brand'],
                responses={201: MatchSerializer}
            )
            def like(self, request, *args, **kwargs):
                return super().like(request, *args, **kwargs)

            @extend_schema(
                tags=['Brand'],
                description="Instant cooperation.\n\n"
                            "Returns match instance.\n\n"
                            "If instant room already exists, will raise BadRequest exception (400)\n\n"
                            "After calling this method you should use room id "
                            "to connect to the room and send a message.\n\n"
                            "Only 1 message can be created by the user.\n\n"
                            "Requires target to be liked by the user. Otherwise, permission will be denied (403).\n\n"
                            "Business subscription only.",
                responses={201: InstantCoopSerializer}
            )
            def instant_coop(self, request, *args, **kwargs):
                return super().instant_coop(request, *args, **kwargs)

            @extend_schema(
                tags=['Brand'],
                description="Get a list of brands that liked the current one.\n\n"
                            "Excludes matches and likes of current brand.\n\n"
                            "Authenticated brand with active subscription only.",
                responses={200: LikedBySerializer(many=True)},
                parameters=[] + get_schema_standard_pagination_parameters()
            )
            def liked_by(self, request, *args, **kwargs):
                return super().liked_by(request, *args, **kwargs)

            @extend_schema(
                tags=['Brand'],
                description="Get a list of liked brands.\n\n"
                            "instant_room: id of a room of type 'I' if it already exists OR null if it doesn't.\n\n"
                            "Authenticated brand with active subscription only.",
                responses={200: MyLikesSerializer(many=True)},
                parameters=[] + get_schema_standard_pagination_parameters()
            )
            def my_likes(self, request, *args, **kwargs):
                return super().my_likes(request, *args, **kwargs)

            @extend_schema(
                tags=['Brand'],
                description="Get a list of matches of the current brand.\n\n"
                            "match_room: id of a room of type 'M'\n\n"
                            "Authenticated brand with active subscription only.",
                responses={200: MyMatchesSerializer(many=True)},
                parameters=[] + get_schema_standard_pagination_parameters()
            )
            def my_matches(self, request, *args, **kwargs):
                return super().my_matches(request, *args, **kwargs)

            @extend_schema(
                tags=['Brand'],
                description="Get a list of recommended brands.\n\n"
                            "Supports filtering.\n\n"
                            "Filters are joined using AND statement.\n\n"
                            "Authenticated brand with active subscription only.",
                parameters=[
                    OpenApiParameter(
                        'avg_bill',
                        OpenApiTypes.INT,
                        OpenApiParameter.QUERY,
                        description='Filter by average bill.\n\n'
                                    'Positive integers only.'
                    ),
                    OpenApiParameter(
                        'subs_count',
                        OpenApiTypes.INT,
                        OpenApiParameter.QUERY,
                        description='Filter by number of subscribers.\n\n'
                                    'Positive integers only.'
                    ),
                    OpenApiParameter(
                        'category',
                        OpenApiTypes.INT,
                        OpenApiParameter.QUERY,
                        many=True,
                        description='Filter by categories.\n\n'
                                    'If brand has at least one of the specified categories it will be included.'
                    ),
                    OpenApiParameter(
                        'city',
                        OpenApiTypes.INT,
                        OpenApiParameter.QUERY,
                        many=True,
                        description='Filter by cities (geo).\n\n'
                                    'Up to 10 cities.\n\n'
                                    'If brand has at least one of the specified cities it will be included.'
                    ),
                ] + get_schema_standard_pagination_parameters(),
                responses={200: RecommendedBrandsSerializer(many=True)}
            )
            def recommended_brands(self, request, *args, **kwargs):
                return super().recommended_brands(request, *args, **kwargs)

            @extend_schema(
                tags=['Brand'],
                description="Get statistics for the brand.\n\n"
                            "The result will be a list of like/match/collab counts for each period.\n\n"
                            "Each period is calculated by subtracting 1 month from the previous one.\n\n"
                            "For example:\n\n"
                            "\tfirst period will be calculated as: "
                            "<current date-time - 1 month> to <current date-time>\n\n"
                            "If today is 13th January, then first period will be: 13th December - 13th January\n\n"
                            "\tsecond period will be calculated as: "
                            "<first period lower bound - 1 month> to <first period lower bound>\n\n"
                            "Continuing example with 13th January, the second period will be: "
                            "13th November - 13th December\n\n"
                            "And so on.\n\n"
                            "Authenticated brand with active subscription only.",
                parameters=[
                    OpenApiParameter(
                        'period',
                        OpenApiTypes.INT,
                        OpenApiParameter.QUERY,
                        required=True,
                        description='Number of months to calculate statistics for.\n\n'
                                    'Statistics will be calculated for range:\n\n'
                                    '\t[now - {period} months, now]\n\n'
                                    'Constraints:\n\n'
                                    '\tmin: 1\n\n'
                                    '\tmax: 12'
                    )
                ],
                responses={200: StatisticsSerializer(many=True)}
            )
            def statistics(self, request, *args, **kwargs):
                return super().statistics(request, *args, **kwargs)

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


class Fix3(OpenApiViewExtension):
    target_class = 'core.apps.brand.api.CollaborationCreateView'

    def view_replacement(self):
        @extend_schema(tags=['Collaboration'])
        class Fixed(self.target_class):
            """
            Report about collaboration with brand.

            match: id of a match to report collaboration about

            Authenticated brand with active subscription only.
            """
            pass

        return Fixed


def brand_me_postprocessing_hook(result, generator, request, public):
    description = {
        'get': {
            'description': 'Получить данные авторизованного бренда'
        },
        'patch': {
            'description': 'Частичное обновление бренда\n\n'
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
        },
        'delete': {'description': 'Удалить бренд'}
    }

    methods = ['get', 'patch', 'delete']
    endpoints = ['/api/v1/brand/me/']

    for endpoint in endpoints:
        for method in methods:
            schema = result['paths'][endpoint][method]
            schema.update(description[method])

    return result
