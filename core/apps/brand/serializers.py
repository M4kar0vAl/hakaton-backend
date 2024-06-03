from django.contrib.auth import get_user_model
from rest_framework import serializers, exceptions

from core.apps.accounts.serializers import CreateUserSerializer
from core.apps.brand.models import Brand, Category, Formats, Goals, Subscription

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', ]


class FormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Formats
        fields = ['name', ]


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goals
        fields = ['name', ]


class SubscriptionSerializer(serializers.ModelSerializer):
    duration = serializers.DurationField()

    class Meta:
        model = Subscription
        fields = ['name', 'cost', 'duration']


class BrandCreateSerializer(serializers.ModelSerializer):
    user = CreateUserSerializer()
    business_category = CategorySerializer()
    formats = FormatSerializer(many=True)
    goal = GoalSerializer(many=True)
    collab_with = CategorySerializer(many=True)
    subscription = SubscriptionSerializer()

    class Meta:
        model = Brand
        exclude = []

    def validate(self, attrs):
        category_name = attrs.get('business_category').get('name')

        if not Category.objects.filter(name=category_name).exists():
            raise exceptions.ValidationError(f'Category {category_name} does not exist.')

        subscription_data = attrs.get('subscription')

        if not Subscription.objects.filter(**subscription_data).exists():
            raise exceptions.ValidationError(f'Subscription {subscription_data.get("name")} does not exist.')

        return attrs

    def create(self, validated_data):
        """
        Метод для создания бренда. Здесь обрабатываются поля-внешние ключи
        """

        category_name = validated_data.pop('business_category').get('name')
        subscription_data = validated_data.pop('subscription')

        category = Category.objects.get(name=category_name)
        subscription = Subscription.objects.get(**subscription_data)

        # Получаем данные по m2m полям
        formats_data = validated_data.pop('formats')
        goals_data = validated_data.pop('goal')
        collab_with_data = validated_data.pop('collab_with')

        # Создаем объект бренда в БД на основе имеющихся данных (без many-to-many полей)
        # TODO добавить обработку создания пользователя
        brand = Brand.objects.create(business_category=category, subscription=subscription,
                                     **validated_data)

        # Получаем объекты для m2m связей
        format_objects = (Formats.objects.get(**format_data) for format_data in formats_data)
        goal_objects = (Goals.objects.get(**goal_data) for goal_data in goals_data)
        collab_with_objects = (Category.objects.get(**collab_with) for collab_with in collab_with_data)

        # Добавляем связи с этими объектами
        brand.formats.add(*format_objects)
        brand.goal.add(*goal_objects)
        brand.collab_with.add(*collab_with_objects)

        return brand


class BrandGetSerializer(serializers.ModelSerializer):
    user = CreateUserSerializer()
    business_category = CategorySerializer()
    formats = FormatSerializer(many=True)
    goal = GoalSerializer(many=True)
    collab_with = CategorySerializer(many=True)
    subscription = SubscriptionSerializer()

    class Meta:
        model = Brand
        exclude = []
