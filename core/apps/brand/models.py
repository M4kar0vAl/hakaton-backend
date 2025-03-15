import os
import uuid

from cities_light.models import City
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.deconstruct import deconstructible


@deconstructible
class UserDirectoryPath:
    """
    Construct path to user directory.

    Accepts field as an argument.
    Returns callable to use as ImageField and FileField upload_to callable

    Need this for migrations to work.
    https://code.djangoproject.com/ticket/22999
    """

    def __init__(self, field: str):
        self.field = field

    def __call__(self, instance, filename):
        from core.apps.brand.utils import get_file_extension

        # file will be uploaded to MEDIA_ROOT/user_<id>/<field>.<extension>
        extension = get_file_extension(filename)
        new_filename = self.field + extension
        return os.path.join(f'user_{instance.user.id}', f'{new_filename}')


def product_photo_path(instance, filename):
    from core.apps.brand.utils import get_file_extension

    # file will be uploaded to MEDIA_ROOT/user_<id>/product_photos/<format>/<uuid4>.<ext>
    format_ = None
    instance_class = instance.__class__
    match instance.format:
        case instance_class.MATCH:
            format_ = 'match'
        case instance_class.CARD:
            format_ = 'brand_card'
        case _:
            pass

    extension = get_file_extension(filename)
    new_filename = f'{uuid.uuid4()}{extension}'

    return f'user_{instance.brand.user.id}/product_photos/{format_}/{new_filename}'


def gallery_path(instance, filename):
    from core.apps.brand.utils import get_file_extension

    # file will be uploaded to MEDIA_ROOT/user_<id>/gallery/<uuid4>.<ext>
    extension = get_file_extension(filename)
    new_filename = f'{uuid.uuid4()}{extension}'
    return f'user_{instance.brand.user.id}/gallery/{new_filename}'


class Brand(models.Model):
    user = models.OneToOneField(
        to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='Пользователь'
    )
    published = models.BooleanField(
        default=False, verbose_name='Опубликовано'
    )

    # PART 1 (everything is required except social media and marketplaces)
    tg_nickname = models.CharField('Ник в телеграме', blank=True, max_length=64)
    city = models.ForeignKey(
        to=City, on_delete=models.SET_NULL, null=True, related_name='brands', verbose_name='Город'
    )
    name = models.CharField(max_length=256, verbose_name='Название бренда')
    position = models.CharField(max_length=256, verbose_name='Должность')
    category = models.ForeignKey(
        to='Category', on_delete=models.PROTECT, related_name='brands', verbose_name='Категория'
    )

    # -----social media urls----
    # max_length of URLField defaults to 200 characters
    inst_url = models.URLField(blank=True, verbose_name='Бренд в Instagram')
    vk_url = models.URLField(blank=True, verbose_name='Бренд в ВК')
    tg_url = models.URLField(blank=True, verbose_name='Бренд в Telegram')
    # --------------------------

    # -----marketplace urls-----
    wb_url = models.URLField(blank=True, verbose_name='Магазин в ВБ')
    lamoda_url = models.URLField(blank=True, verbose_name='Магазин в Lamoda')
    site_url = models.URLField(blank=True, verbose_name='Сайт бренда')
    # --------------------------

    subs_count = models.PositiveIntegerField(verbose_name='Кол-во подписчиков')
    avg_bill = models.PositiveIntegerField(verbose_name='Средний чек')
    tags = models.ManyToManyField(to='Tag', related_name='brands', verbose_name='Ценности')
    uniqueness = models.CharField(max_length=512, verbose_name='Уникальность бренда')
    logo = models.ImageField('Лого', upload_to=UserDirectoryPath('logo'))
    photo = models.ImageField('Фото представителя', upload_to=UserDirectoryPath('photo'))

    # PART 2 (optional fields)
    mission_statement = models.CharField('Миссия бренда', blank=True, max_length=512)
    formats = models.ManyToManyField(
        to='Format', related_name='brands', blank=True, verbose_name='Форматы коллабораций'
    )
    goals = models.ManyToManyField(to='Goal', related_name='brands', blank=True, verbose_name='Бизнес задачи')
    offline_space = models.CharField(max_length=512, blank=True, verbose_name='Оффлайн пространство')
    problem_solving = models.CharField(
        'Какую проблему решает', blank=True, max_length=512
    )
    target_audience = models.OneToOneField(
        'TargetAudience', on_delete=models.PROTECT, blank=True, null=True, verbose_name='Целевая аудитория'
    )
    categories_of_interest = models.ManyToManyField(
        to='Category', related_name='brands_as_interest', blank=True, verbose_name='Интересующие категории'
    )

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'

    def __str__(self):
        return f'Brand: {self.name}'

    def __repr__(self):
        return (
            f'{self.__class__.__name__}(user_id={self.user_id}, name="{self.name}", tg_nickname="{self.tg_nickname}", '
            f'city_id={self.city_id}, position="{self.position}", category_id={self.category_id}, '
            f'inst_url="{self.inst_url}", vk_url="{self.vk_url}", tg_url="{self.tg_url}", wb_url="{self.wb_url}", '
            f'lamoda_url="{self.lamoda_url}", site_url="{self.site_url}", subs_count={self.subs_count}, '
            f'avg_bill={self.avg_bill}, uniqueness="{self.uniqueness}", logo="{self.logo}", photo="{self.photo}", '
            f'mission_statement="{self.mission_statement}", offline_space="{self.offline_space}", '
            f'problem_solving="{self.problem_solving}")'
        )


class Blog(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='blogs', verbose_name='Бренд')
    blog = models.URLField(verbose_name='Блог')


class Category(models.Model):
    name = models.CharField(max_length=128, verbose_name='Категория')
    is_other = models.BooleanField(default=False, verbose_name='Другое')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return f'Category: {self.name}'

    def __repr__(self):
        return f'Category: {self.name}'


class Format(models.Model):
    name = models.CharField(max_length=128, verbose_name='Формат')
    is_other = models.BooleanField(default=False, verbose_name='Другое')

    class Meta:
        verbose_name = 'Формат'
        verbose_name_plural = 'Форматы'

    def __str__(self):
        return f'Format: {self.name}'

    def __repr__(self):
        return f'Format: {self.name}'


class Goal(models.Model):
    name = models.CharField(max_length=128, verbose_name='Бизнес задача')
    is_other = models.BooleanField(default=False, verbose_name='Другое')

    class Meta:
        verbose_name = 'Бизнес задача'
        verbose_name_plural = 'Бизнес задачи'

    def __str__(self):
        return f'Goal: {self.name}'

    def __repr__(self):
        return f'Goal: {self.name}'


# Tag model aka ценности
class Tag(models.Model):
    name = models.CharField(max_length=100, verbose_name='Тег')
    is_other = models.BooleanField(default=False, verbose_name='Другое')

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return f'Tag: {self.name}'

    def __repr__(self):
        return f'Tag: {self.name}'


# ----------target audience models----------
class Age(models.Model):
    men = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Мужчины'
    )
    women = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Женщины'
    )

    class Meta:
        verbose_name = 'Возраст'
        verbose_name_plural = 'Возрасты'

    def __str__(self):
        return f'Age pk: {self.pk}'

    def __repr__(self):
        return f'Age pk: {self.pk}'


class Gender(models.Model):
    men = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='% мужчин'
    )
    women = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='% женщин'
    )

    class Meta:
        verbose_name = 'Пол'
        verbose_name_plural = 'Пол'

    def __str__(self):
        return f'Gender pk: {self.pk}'

    def __repr__(self):
        return f'Gender pk: {self.pk}'


class GEO(models.Model):
    city = models.ForeignKey(to=City, on_delete=models.CASCADE, related_name='geos', verbose_name='Город')
    people_percentage = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Процент людей'
    )
    target_audience = models.ForeignKey(
        'TargetAudience', on_delete=models.CASCADE, related_name='geos', verbose_name='Целевая аудитория'
    )

    class Meta:
        verbose_name = 'ГЕО'
        verbose_name_plural = 'ГЕО'

    def __str__(self):
        return f'GEO: {self.city} - {self.people_percentage}'

    def __repr__(self):
        return f'GEO: {self.city} - {self.people_percentage}%'


class TargetAudience(models.Model):
    age = models.OneToOneField(
        Age, on_delete=models.SET_NULL, blank=True, null=True, related_name='target_audience', verbose_name='Возраст'
    )
    gender = models.OneToOneField(
        Gender, on_delete=models.SET_NULL, blank=True, null=True, related_name='target_audience', verbose_name='Пол'
    )
    income = models.PositiveIntegerField(
        validators=[MinValueValidator(50000), MaxValueValidator(1000000)],
        blank=True,
        null=True,
        verbose_name='Доход'
    )

    class Meta:
        verbose_name = 'Целевая аудитория'
        verbose_name_plural = 'Целевая аудитория'

    def __str__(self):
        return f'Target audience: {self.pk}'

    def __repr__(self):
        return f'Target audience: {self.pk}'


# ------------------------------------------


class ProductPhoto(models.Model):
    MATCH = 'M'
    CARD = 'C'
    FORMAT_CHOICES = {
        MATCH: 'Для метча',
        CARD: 'Для карточки бренда'
    }
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='product_photos', verbose_name='Бренд')
    format = models.CharField(max_length=1, choices=FORMAT_CHOICES, verbose_name='Формат изображения')
    image = models.ImageField(upload_to=product_photo_path, verbose_name='Фото')

    class Meta:
        verbose_name = 'Фото продукта'
        verbose_name_plural = 'Фото продукта'

    def __str__(self):
        return f'Product photo: {self.pk}'

    def __repr__(self):
        return f'Product photo: {self.pk}'


class GalleryPhoto(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='gallery_photos', verbose_name='Бренд')
    image = models.ImageField(upload_to=gallery_path, verbose_name='Фото')

    class Meta:
        verbose_name = 'Фото для галереи'
        verbose_name_plural = 'Фото для галереи'

    def __str__(self):
        return f'Gallery photo: {self.pk}'

    def __repr__(self):
        return f'Gallery photo: {self.pk}'


class Match(models.Model):
    initiator = models.ForeignKey(
        to=Brand,
        on_delete=models.PROTECT,
        related_name='initiator',
        verbose_name='Кто лайкнул'
    )

    target = models.ForeignKey(
        to=Brand,
        on_delete=models.PROTECT,
        related_name='target',
        verbose_name='Кого лайкнули'
    )

    is_match = models.BooleanField(
        default=False, verbose_name='Метч'
    )

    room = models.OneToOneField(
        'chat.Room', on_delete=models.SET_NULL, blank=True, null=True
    )

    like_at = models.DateTimeField(auto_now_add=True, verbose_name='Время лайка')
    match_at = models.DateTimeField(null=True, default=None, verbose_name='Время метча')


class BusinessGroup(models.Model):
    brand = models.ForeignKey(
        to=Brand, on_delete=models.CASCADE, related_name='business_groups', verbose_name='Бренд'
    )
    name = models.CharField(max_length=200, verbose_name='Название или ссылка')


class Collaboration(models.Model):
    reporter = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name='collab_reporter', verbose_name='Кто поделился'
    )
    collab_with = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name='collab_participant', verbose_name='Коллаборация с'
    )

    match = models.ForeignKey(
        Match, on_delete=models.PROTECT, related_name='collaborations', verbose_name='Метч'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    # overall success
    success_assessment = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name='Оценка по 10 бальной шкале'
    )
    success_reason = models.CharField(max_length=512, verbose_name='Причина успеха')
    to_improve = models.CharField(max_length=512, verbose_name='Что улучшить')

    # quantitative indicators
    subs_received = models.IntegerField(verbose_name='Получено подписчиков')
    leads_received = models.IntegerField(verbose_name='Получено лидов/заявок')
    sales_growth = models.CharField(max_length=128, verbose_name='Прирост продаж')
    audience_reach = models.PositiveIntegerField(verbose_name='Охват аудитории')
    bill_change = models.CharField(max_length=128, verbose_name='Изменение ср. чека')

    # partnership
    new_offers = models.BooleanField(verbose_name='Новые предложения')
    new_offers_comment = models.CharField(max_length=512, blank=True, verbose_name='Комментарий про предложения')

    # reputation
    perception_change = models.BooleanField(verbose_name='Изменение восприятия бренда')

    # compliance
    brand_compliance = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name='Соответствие брендов'
    )

    # platform interaction
    platform_help = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Помощь платформы'
    )
    difficulties = models.BooleanField(verbose_name='Трудности')
    difficulties_comment = models.CharField(max_length=512, blank=True, verbose_name='Комментарий про трудности')
