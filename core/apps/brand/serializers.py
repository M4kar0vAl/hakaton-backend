import base64
import uuid
from copy import copy

from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers, exceptions

from core.apps.accounts.serializers import CreateUserSerializer
from core.apps.brand.models import (
    Brand,
    Category,
    Format,
    Goal,
    PresenceType,
    ReadinessPublicSpeaker,
    SubsCount,
    AvgBill,
    CollaborationInterest,
)
from core.apps.questionnaire.models import AnswerChoice
from core.apps.payments.serializers import SubscriptionSerializer


User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['text', 'question']
        extra_kwargs = {
            'question': {'write_only': True},
        }


class PresenceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PresenceType
        fields = ['text', 'question']
        extra_kwargs = {
            'question': {'write_only': True},
        }


class ReadinessPublicSpeakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadinessPublicSpeaker
        fields = ['text', 'question']
        extra_kwargs = {
            'question': {'write_only': True},
        }


class SubsCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubsCount
        fields = ['text', 'question']
        extra_kwargs = {
            'question': {'write_only': True},
        }


class AvgBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvgBill
        fields = ['text', 'question']
        extra_kwargs = {
            'question': {'write_only': True},
        }


class CollaborationInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['text', 'question']
        extra_kwargs = {
            'question': {'write_only': True},
        }


class FormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Format
        fields = ['text', 'question']
        extra_kwargs = {
            'question': {'write_only': True},
        }


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ['text', 'question']
        extra_kwargs = {
            'question': {'write_only': True},
        }


class BrandCreateSerializer(serializers.ModelSerializer):
    errors_messages = {
        'category': 'Invalid value for text: {category}',
        'presence_type': 'Invalid value for text: {presence_type}',
        'public_speaker': 'Invalid value for text: {public_speaker}.',
        'subs_count': 'Invalid value for text: {subs_count}',
        'avg_bill': 'Invalid value for text: {avg_bill}',
        'goals': 'Invalid value for text: {goal}',
        'formats': 'Invalid value for text: {format_}',
        'collaboration_interest': 'Invalid value for text: {business}',
    }
    fails = {}

    user = CreateUserSerializer(read_only=True)
    subscription = SubscriptionSerializer(read_only=True)
    category = CategorySerializer()
    presence_type = PresenceTypeSerializer()
    public_speaker = ReadinessPublicSpeakerSerializer()
    subs_count = SubsCountSerializer()
    avg_bill = AvgBillSerializer()
    goals = GoalSerializer(many=True)
    formats = FormatSerializer(many=True)
    collaboration_interest = CollaborationInterestSerializer(many=True)

    class Meta:
        model = Brand
        read_only_fields = ['sub_expire']
        exclude = ['published', ]

    def to_internal_value(self, data):
        for field in ['logo', 'photo', 'product_photo']:
            img_b64 = data[field]
            data[field] = self.convert_b64str_to_img(img_b64)

        return super().to_internal_value(data)

    def validate(self, attrs):
        self.fails = {}
        # one-to-one

        category = attrs.get('category')
        presence_type = attrs.get('presence_type')
        public_speaker = attrs.get('public_speaker')
        subs_count = attrs.get('subs_count')
        avg_bill = attrs.get('avg_bill')

        # FK
        goals = attrs.get('goals')
        formats = attrs.get('formats')
        collaboration_interest = attrs.get('collaboration_interest')

        if not AnswerChoice.objects.filter(**category).exists():
            self.efail('category', category=category)

        if not AnswerChoice.objects.filter(**presence_type).exists():
            self.efail('presence_type', presence_type=presence_type)

        if not AnswerChoice.objects.filter(**public_speaker).exists():
            self.efail('public_speaker', public_speaker=public_speaker)

        if not AnswerChoice.objects.filter(**subs_count).exists():
            self.efail('subs_count', subs_count=subs_count)

        if not AnswerChoice.objects.filter(**avg_bill).exists():
            self.efail('avg_bill', avg_bill=avg_bill)

        for goal in goals:
            if goal['text'].startswith('Свой вариант'):
                continue
            elif not AnswerChoice.objects.filter(**goal).exists():
                self.efail('goals', goal=goal)

        for format_ in formats:
            if not AnswerChoice.objects.filter(**format_).exists():
                self.efail('formats', format_=format_)

        for business in collaboration_interest:
            if not AnswerChoice.objects.filter(**business).exists():
                self.efail('collaboration_interest', business=business)

        if self.fails:
            raise exceptions.ValidationError(
                detail=self.fails
            )

        return attrs

    def create(self, validated_data):
        """
        Метод для создания бренда. Здесь обрабатываются поля-внешние ключи
        """
        user = self.context['request'].user

        # one-to-one
        category = validated_data.pop('category')
        presence_type = validated_data.pop('presence_type')
        public_speaker = validated_data.pop('public_speaker')
        subs_count = validated_data.pop('subs_count')
        avg_bill = validated_data.pop('avg_bill')

        # FK
        goals = validated_data.pop('goals')
        formats = validated_data.pop('formats')
        collaboration_interest = validated_data.pop('collaboration_interest')

        # Создаем объект бренда в БД и связанных моделей
        with transaction.atomic():
            brand = Brand.objects.create(user_id=user.id, **validated_data)

            # записываем ответы анкеты
            Category.objects.create(brand=brand, **category)
            PresenceType.objects.create(brand=brand, **presence_type)
            ReadinessPublicSpeaker.objects.create(brand=brand, **public_speaker)
            SubsCount.objects.create(brand=brand, **subs_count)
            AvgBill.objects.create(brand=brand, **avg_bill)

            # записываем ответы для FK связей
            [Format.objects.create(brand=brand, **obj) for obj in formats]
            [CollaborationInterest.objects.create(
                brand=brand, **obj
            ) for obj in collaboration_interest]

            for goal in goals:
                if goal['text'].startswith('Свой вариант: '):
                    goal['text'] = goal['text'].lstrip('Свой вариант: ')
                Goal.objects.create(brand=brand, **goal)

        return brand

    def efail(self, key: str, **kwargs) -> None:
        msg = self.errors_messages[key].format(**kwargs)
        self.fails.update({key: msg})

    def convert_b64str_to_img(self, img_str: str) -> InMemoryUploadedFile:
        file_name = f"{uuid.uuid4()}.png"
        image_data = base64.b64decode(img_str)
        image_io = BytesIO(image_data)

        django_img = InMemoryUploadedFile(
            file=image_io,
            field_name=None,
            name=file_name,
            content_type='image/png',
            size=image_io.getbuffer().nbytes,
            charset=None
        )
        return django_img


class BrandGetSerializer(serializers.ModelSerializer):
    user = CreateUserSerializer(read_only=True)
    subscription = SubscriptionSerializer(read_only=True)
    category = CategorySerializer()
    presence_type = PresenceTypeSerializer()
    public_speaker = ReadinessPublicSpeakerSerializer()
    subs_count = SubsCountSerializer()
    avg_bill = AvgBillSerializer()
    goals = GoalSerializer(many=True)
    formats = FormatSerializer(many=True)
    collaboration_interest = CollaborationInterestSerializer(many=True)

    class Meta:
        model = Brand
        exclude = []
