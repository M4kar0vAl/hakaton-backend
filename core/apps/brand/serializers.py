from django.contrib.auth import get_user_model
from rest_framework import serializers, exceptions

from core.apps.accounts.serializers import UserSerializer
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


class BrandSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    business_category = CategorySerializer()
    formats = FormatSerializer(many=True)
    goal = GoalSerializer(many=True)
    collab_with = CategorySerializer(many=True)
    subscription = SubscriptionSerializer()

    class Meta:
        model = Brand
        exclude = []

    def create(self, validated_data):
        """
        Метод для создания бренда. Здесь обрабатываются поля-внешние ключи
        """
        # СНАЧАЛА РАБОТАЕМ С ONE-TO-ONE И FK

        # Получаем введенные данные пользователя
        user_data = validated_data.pop('user')

        # Пытаемся получить пользователя из БД (возможно будет нужно для предрегистрации!)
        try:
            user = User.objects.get(email=user_data.get('email'))
        except User.DoesNotExist:
            user = None

        # Если пользователя нет - создаем
        if not user:
            user = User.objects.create(**user_data)

        # Получаем название категории
        category_name = validated_data.pop('business_category').get('name')

        # Пытаемся получить категорию из БД.
        # Если не находим - генерируем исключение 404, т.к. категории строго предопределены
        try:
            category = Category.objects.get(name=category_name)
        except Category.DoesNotExist:
            raise exceptions.NotFound(f'Category {category_name} does not exist.')

        # Получаем данные по подписке
        subscription_data = validated_data.pop('subscription')

        # Пытаемся получить подписку из БД.
        # Если не находим - генерируем исключение 404, т.к. подписки строго предопределены
        try:
            subscription = Subscription.objects.get(**subscription_data)
        except Subscription.DoesNotExist:
            raise exceptions.NotFound(f'Subscription {subscription_data.get("name")} does not exist.')

        # ЗАТЕМ ПЕРЕХОДИМ К MANY-TO-MANY

        # Получаем данные по m2m полям
        formats_data = validated_data.pop('formats')
        goals_data = validated_data.pop('goal')
        collab_with_data = validated_data.pop('collab_with')

        # Создаем объект бренда в БД на основе имеющихся данных (без many-to-many полей)
        brand = Brand.objects.create(user_id=user, business_category=category, subscription=subscription,
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
