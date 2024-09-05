import base64
import uuid
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction, DatabaseError
from rest_framework import serializers, exceptions

from core.apps.accounts.serializers import CreateUserSerializer
from core.apps.analytics.utils import log_match_activity
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
    Match,
)
from core.apps.chat.models import Room
from core.apps.payments.serializers import SubscriptionSerializer
from core.apps.questionnaire.models import AnswerChoice

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


class GetShortBrandSerializer(serializers.ModelSerializer):
    category = CategorySerializer()

    class Meta:
        model = Brand
        fields = [
            'id',
            'brand_name_pos',
            'fullname',
            'logo',
            'photo',
            'product_photo',
            'category'
        ]
        read_only_fields = [
            'id',
            'brand_name_pos',
            'fullname',
            'logo'
            'photo',
            'product_photo',
            'category'
        ]


class MatchSerializer(serializers.ModelSerializer):
    target = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), write_only=True)

    class Meta:
        model = Match
        exclude = ['id', 'initiator']
        read_only_fields = ['is_match', 'room']

    def validate(self, attrs):
        initiator = self.context['request'].user.brand
        target = attrs.get('target')

        if initiator == target:
            raise exceptions.ValidationError("You cannot 'like' yourself")

        try:
            # check if this brand have already performed that same 'like' action
            match = Match.objects.get(initiator=initiator, target=target)
            if match.is_match:
                raise exceptions.ValidationError(f"You already have 'match' with this brand! Room id: {match.room.pk}.")
            raise exceptions.ValidationError("You have already 'liked' this brand!")
        except Match.DoesNotExist:
            # at this point it means that there is no entry in db with that initiator and target,
            # BUT there may be a reverse entry, which is checked further
            pass

        try:
            # check if there is match
            match = Match.objects.get(initiator=target, target=initiator)
        except Match.DoesNotExist:
            match = None

        if match is not None and match.is_match:
            # if is_match = True already, then raise an exception
            raise exceptions.ValidationError(f"You already have 'match' with this brand! Room id: {match.room.pk}.")

        # at this point match is either None or is_match = False, passed to create method
        attrs['match'] = match
        attrs['initiator'] = initiator

        return attrs

    def create(self, validated_data):
        initiator = validated_data.get('initiator')
        target = validated_data.get('target')  # target contains Brand obj
        match = validated_data.get('match')

        try:
            with transaction.atomic():
                if match is not None:
                    # if not None, then is_match is False (checked in validate)
                    match.is_match = True
                    has_business = any([  # TODO change business sub definition
                        initiator.subscription and initiator.subscription.name == 'Бизнес',
                        target.subscription and target.subscription.name == 'Бизнес'
                    ])
                    room = Room.objects.create(has_business=has_business)
                    # room.participants.add(initiator, target)
                    room.participants.add(initiator.user, target.user)
                    match.room = room
                    match.save()
                else:
                    match = Match.objects.create(initiator=initiator, target=target)

                log_match_activity(initiator=initiator, target=target, is_match=match.is_match)
        except DatabaseError:
            raise exceptions.ValidationError("Failed to perform action!")

        return match


class InstantCoopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        exclude = []
        read_only_fields = ['id', 'participants', 'has_business', 'type']

    def validate(self, attrs):
        initiator = self.context['request'].user.brand
        target_id = self.context['target_id']

        if initiator.pk == target_id:
            raise exceptions.ValidationError("You cannot cooperate with yourself!")

        try:
            target = Brand.objects.get(pk=target_id)
        except Brand.DoesNotExist:
            raise exceptions.NotFound(f"Brand with id: {target_id} not found!")

        try:
            # intersection of querysets
            # if initiator's instant rooms queryset and target's instant rooms queryset has common room,
            # then it means that they already have instant cooperation. No need to make another room
            common_room = (
                # initiator.rooms.filter(type=Room.INSTANT) & target.rooms.filter(type=Room.INSTANT)
                    initiator.user.rooms.filter(type=Room.INSTANT) & target.user.rooms.filter(type=Room.INSTANT)
            ).get()
            # if common room exist, then raise an exception.
            raise exceptions.ValidationError(f"You already have a chat with this brand! Room id: {common_room.pk}.")
        except Room.DoesNotExist:
            # if common room does not exist, then everything is fine. Continue and create one.
            pass

        attrs['initiator'] = initiator
        attrs['target'] = target

        return attrs

    def create(self, validated_data):
        initiator = validated_data.get('initiator')
        target = validated_data.get('target')

        room = Room.objects.create(has_business=True, type=Room.INSTANT)
        # room.participants.add(initiator, target)
        room.participants.add(initiator.user, target.user)

        return room


class InstantCoopRequestSerializer(serializers.Serializer):
    target = serializers.IntegerField(write_only=True)
