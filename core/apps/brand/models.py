from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from core.apps.payments.models import Subscription
from core.apps.questionnaire.models import Question


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    # in case of brand there will be a user_{id} directory with 3 files:
    # - logo_{uuid}.png
    # - photo_{uuid}.png
    # - product_photo_{uuid}.png
    return f'user_{instance.user.id}/{filename}'


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
        null=True
    )
    sub_expire = models.DateField("Окончание подписки", null=True)
    tg_nickname = models.CharField('Ник в телеграме', max_length=64)
    brand_name_pos = models.CharField(
        'Название бренда и должность',
        max_length=512
    )
    inst_brand_url = models.CharField('Бренд в Instagram', max_length=512)
    brand_site_url = models.CharField('Сайт бренда', max_length=512)
    topics = models.CharField('Темы', max_length=512)
    mission_statement = models.CharField('Миссия бренда', max_length=512)
    target_audience = models.CharField(
        'Целевая аудитория', max_length=512
    )
    unique_product_is = models.CharField(
        'Уникальность продукта', max_length=512
    )
    product_description = models.CharField(
        'Описание продукта', max_length=512
    )
    problem_solving = models.CharField(
        'Какую проблему решает', max_length=512
    )
    business_group = models.CharField(
        'Сообщество предпринимателей', max_length=512
    )
    logo = models.ImageField('Лого', upload_to=user_directory_path, null=True)
    photo = models.ImageField(
        'Фото представителя', upload_to=user_directory_path, null=True
    )
    product_photo = models.ImageField(
        'Фото продукта', upload_to=user_directory_path, null=True
    )
    fullname = models.CharField('Фамилия и имя', max_length=512)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'

    def __repr__(self):
        return f'Brand name and position: {self.brand_name_pos}'


class Category(models.Model):
    brand = models.OneToOneField(
        Brand,
        on_delete=models.PROTECT,
        related_name='category',
    )
    text = models.CharField(max_length=128)
    question = models.ForeignKey(
        Question, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __repr__(self):
        return f'Category: {self.text}'


class PresenceType(models.Model):
    brand = models.OneToOneField(
        Brand,
        on_delete=models.PROTECT,
        related_name='presence_type'
    )
    text = models.CharField(max_length=128)
    question = models.ForeignKey(
        Question, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        verbose_name = 'Способ размещения бренда'
        verbose_name_plural = 'Способы размещения бренда'

    def __repr__(self):
        return f'PresenceType: {self.text}'


class ReadinessPublicSpeaker(models.Model):
    brand = models.OneToOneField(
        Brand,
        on_delete=models.PROTECT,
        related_name='public_speaker'
    )
    text = models.CharField(max_length=128)
    question = models.ForeignKey(
        Question, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        verbose_name = 'Готовность быть спикером'
        verbose_name_plural = 'Готовность быть спикером'

    def __repr__(self):
        return f'ReadinessPublicSpeaker: {self.text}'


class SubsCount(models.Model):
    brand = models.OneToOneField(
        Brand,
        on_delete=models.PROTECT,
        related_name='subs_count'
    )
    text = models.CharField(max_length=128)
    question = models.ForeignKey(
        Question, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        verbose_name = 'Кол-во подписчиков'
        verbose_name_plural = 'Кол-во подписчиков'

    def __repr__(self):
        return f'SubsCount: {self.text}'


class AvgBill(models.Model):
    brand = models.OneToOneField(
        Brand,
        on_delete=models.PROTECT,
        related_name='avg_bill'
    )
    text = models.CharField(max_length=128)
    question = models.ForeignKey(
        Question, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        verbose_name = 'Средний чек'
        verbose_name_plural = 'Средний чек'

    def __repr__(self):
        return f'AvgBill: {self.text}'


class Goal(models.Model):
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='goals'
    )
    text = models.CharField(max_length=128)
    question = models.ForeignKey(
        Question, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        verbose_name = 'Цель'
        verbose_name_plural = 'Цели'

    def __repr__(self):
        return f'Goal: {self.text}'


class Format(models.Model):
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='formats'
    )
    text = models.CharField(max_length=128)
    question = models.ForeignKey(
        Question, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        verbose_name = 'Формат взаимодействия'
        verbose_name_plural = 'Форматы взаимодействия'

    def __repr__(self):
        return f'Format: {self.text}'


class CollaborationInterest(models.Model):
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='collaboration_interest'
    )
    text = models.CharField(max_length=128)
    question = models.ForeignKey(
        Question, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        verbose_name = 'Интересующая коллаборация'
        verbose_name_plural = 'Интересующие коллаборации'

    def __repr__(self):
        return f'CollaborationInterest: {self.text}'


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


class Collaboration(models.Model):
    reporter = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name='collab_reporter', verbose_name='Кто поделился'
    )
    collab_with = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name='collab_participant', verbose_name='Коллаборация с'
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
