from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from core.apps.payments.models import Subscription


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f'user_{instance.user.id}/{filename}'


def product_photo_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/product_photos/<format>/<filename>
    format_ = None
    instance_class = instance.__class__
    match instance.format:
        case instance_class.MATCH:
            format_ = 'match'
        case instance_class.CARD:
            format_ = 'brand_card'
        case _:
            pass

    return f'user_{instance.brand.user.id}/product_photos/{format_}/{filename}'


def gallery_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/gallery/<filename>
    return f'user_{instance.brand.user.id}/gallery/{filename}'


class Brand(models.Model):
    user = models.OneToOneField(
        to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    published = models.BooleanField(
        default=False, verbose_name='Опубликовано'
    )
    subscription = models.ForeignKey(
        to=Subscription,
        on_delete=models.PROTECT,
        related_name='brands',
        verbose_name='Тариф',
        blank=True,
        null=True
    )
    sub_expire = models.DateField("Окончание подписки", null=True)

    # PART 1 (everything is required except social media and marketplaces)
    tg_nickname = models.CharField('Ник в телеграме', blank=True, max_length=64)
    blog_url = models.URLField(blank=True, verbose_name='Блог бренда')
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
    logo = models.ImageField('Лого', upload_to=user_directory_path)
    photo = models.ImageField('Фото представителя', upload_to=user_directory_path)

    # PART 2 (optional fields)
    description = models.CharField(max_length=512, blank=True, verbose_name='Описание бренда')
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

    def __repr__(self):
        return f'Brand: {self.name}'


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
    city = models.CharField(max_length=256, verbose_name='Город')
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
    age = models.OneToOneField(Age, on_delete=models.PROTECT, related_name='target_audience', verbose_name='Возраст')
    gender = models.OneToOneField(Gender, on_delete=models.PROTECT, related_name='target_audience', verbose_name='Пол')
    income = models.PositiveIntegerField(
        validators=[MinValueValidator(50000), MaxValueValidator(1000000)],
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
        default=False,
        verbose_name='Метч'
    )
    room = models.OneToOneField(
        'chat.Room', on_delete=models.SET_NULL, blank=True, null=True
    )


class BusinessGroup(models.Model):
    brand = models.ForeignKey(
        to=Brand, on_delete=models.CASCADE, related_name='business_groups', verbose_name='Бренд'
    )
    name = models.CharField(max_length=200, verbose_name='Название или ссылка')
