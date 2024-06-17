from django.db.models import Q, Model


def generate_q_list(data: list[dict], lookup_field: str) -> list[Q]:
    """
    Генерирует список объектов класса Q.
    Поддерживает django field lookups (https://docs.djangoproject.com/en/4.2/ref/models/querysets/#field-lookups).
    По умолчанию используется exact.
    Чтобы изменить lookup надо в конец строки с названием поля через __ указать нужный lookup. Например: 'pk__gte'.

    Args:
        data: список сериализованных объектов
        lookup_field: поле, по которому в дальнейшем будет производиться поиск в БД
    """
    if not isinstance(data, list):
        raise TypeError('"data" must be a list of dicts')

    if not type(lookup_field) is str:
        raise TypeError('"lookup_field" must be a string')

    kwargs_list = ({lookup_field: obj[lookup_field]} for obj in data)
    q_list = list(map(Q, kwargs_list))

    return q_list


def get_query(q_list: list[Q], combinator: str = '|') -> Q:
    """
    Объединяет список объектов Q класса через combinator.
    Доступные комбинаторы:
        '|': OR (по умолчанию)
        '&': AND
        '^': XOR

    Args:
        q_list: список объектов Q класса для объединения
        combinator: строка длины 1, условие, по которому будут объединены объекты Q
    """
    if not isinstance(q_list, list):
        raise TypeError('"q_list" must be a list')

    if not type(combinator) is str:
        raise TypeError('"combinator" must be a string')

    if len(combinator) != 1:
        raise ValueError('"combinator" must be a single character. Choose from: "|" - OR, "&" - AND, "^" - XOR]')

    query = q_list.pop()

    match combinator:
        case '|':
            while q_list:
                query |= q_list.pop()
        case '&':
            while q_list:
                query &= q_list.pop()
        case '^':
            while q_list:
                query ^= q_list.pop()

    return query


def get_m2m_objects(data: list[dict], model_class: type(Model), lookup_field: str, combinator: str = '|') -> list:
    """
    Забирает из БД объекты, указанные в data.
    Возвращает список объектов модели model_class.

    Args:
        data: список сериализованных объектов
        model_class: класс модели, объекты которой нужно найти
        lookup_field: поле, по которому будет производиться поиск в БД
        combinator: условие, по которому будут объединены lookup_field всех объектов из data
    """
    if not isinstance(model_class, Model):
        raise TypeError('"model_class" must be inherited from django Model class')

    q_list = generate_q_list(data, lookup_field)
    query = get_query(q_list, combinator)

    return list(model_class.objects.filter(query))
