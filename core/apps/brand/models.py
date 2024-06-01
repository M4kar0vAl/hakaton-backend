from django.conf import settings
from django.db import models


class Brand(models.Model):
    SUBSCRIBERS_COUNT = (
        ('1k', '0 - 1000'),
        ('10k', '1000 - 10000'),
        ('100K', '10000 - 100000'),
        ('500k', '100000 - 500000'),
        ('INF', '500000+'),
    )

    AVG_BILL = (
        ('1k', '0 - 1000'),
        ('10k', '1000 - 10000'),
        ('100K', '10000 - 100000'),
        ('500k', '100000 - 500000'),
        ('INF', '500000+'),
    )

    user_id = models.OneToOneField(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # TODO изменить default у published, когда будет реализована модерация
    published = models.BooleanField(default=True, verbose_name='Опубликовано')
    fi = models.CharField(max_length=128, verbose_name='Фамилия и имя')
    birth_date = models.DateField(verbose_name='Дата рождения')
    tg_nickname = models.CharField(max_length=128, verbose_name='Ник в телеграме')
    brand_name_pos = models.CharField(max_length=128, verbose_name='Название бренда и должность')
    business_category = models.ForeignKey(to='Category', on_delete=models.SET_NULL, null=True, related_name='brands',
                                          verbose_name='Категория')
    inst_brand_url = models.URLField(verbose_name='Бренд в Instagram')
    inst_profile_url = models.URLField(verbose_name='Профиль в Instagram')
    tg_brand_url = models.URLField(verbose_name='Telegram-канал')
    brand_site_url = models.URLField(verbose_name='Сайт бренда')
    topics = models.TextField(verbose_name='Темы')
    subs_count = models.CharField(choices=SUBSCRIBERS_COUNT, max_length=4,
                                  verbose_name='Кол-во подписчиков в Instagram')
    avg_bill = models.CharField(choices=AVG_BILL, max_length=4, verbose_name='Средний чек')
    values = models.CharField(max_length=255, verbose_name='Ценности')
    target_audience = models.TextField(verbose_name='Целевая аудитория')
    territory = models.CharField(max_length=128, verbose_name='География бренда')
    formats = models.ManyToManyField(to='Formats', related_name='brands', verbose_name='Форматы')
    goal = models.ManyToManyField(to='Goals', related_name='brands', verbose_name='Цель')
    collab_with = models.ManyToManyField(to='Category', related_name='brand_collab_with',
                                         verbose_name='Категории коллаборации')
    logo = models.ImageField(upload_to='logos', verbose_name='Лого')
    photo = models.ImageField(upload_to='photos', verbose_name='Фото представителя')
    product_photo = models.ImageField(upload_to='product_photos', verbose_name='Фото продукта')
    subscription = models.ForeignKey(to='Subscription', on_delete=models.PROTECT, related_name='brands',
                                     verbose_name='Тариф')
    sub_expire = models.DateField("Окончание подписки", null=True)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'

    def __repr__(self):
        return f'Brand name and position: {self.brand_name_pos}'


class Category(models.Model):
    name = models.CharField(max_length=128, verbose_name='Название категории')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __repr__(self):
        return f'Category: {self.name}'


class Formats(models.Model):
    name = models.CharField(max_length=128, verbose_name='Название формата')

    class Meta:
        verbose_name = 'Формат'
        verbose_name_plural = 'Форматы'

    def __repr__(self):
        return f'Format: {self.name}'


class Goals(models.Model):
    name = models.CharField(max_length=128, verbose_name='Название цели')

    class Meta:
        verbose_name = 'Цель'
        verbose_name_plural = 'Цели'

    def __repr__(self):
        return f'Goal: {self.name}'


class Subscription(models.Model):
    name = models.CharField(max_length=100, verbose_name='Тариф')
    cost = models.PositiveIntegerField(verbose_name='Цена')
    duration = models.DurationField(verbose_name='Продолжительность')

    class Meta:
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'

    def __repr__(self):
        return f'Тариф: {self.name}'
