from django.contrib.auth import get_user_model
from rest_framework import serializers, exceptions

from core.apps.accounts.serializers import CreateUserSerializer
from core.apps.brand.models import Brand, Category, Formats, Goals, Subscription
from core.apps.brand.utils import get_m2m_objects

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

        user_data = attrs.get('user')

        if not User.objects.filter(**user_data).exists():
            raise exceptions.ValidationError(f'User {user_data.get("email")} does not exist.')

        return attrs

    def create(self, validated_data):
        """
        Метод для создания бренда. Здесь обрабатываются поля-внешние ключи
        """

        category_name = validated_data.pop('business_category').get('name')
        subscription_data = validated_data.pop('subscription')
        user_data = validated_data.pop('user')

        category = Category.objects.get(name=category_name)
        subscription = Subscription.objects.get(**subscription_data)
        user = User.objects.get(**user_data)

        # Получаем данные по m2m полям
        formats_data = validated_data.pop('formats')
        goals_data = validated_data.pop('goal')
        collab_with_data = validated_data.pop('collab_with')

        # Создаем объект бренда в БД на основе имеющихся данных (без many-to-many полей)
        brand = Brand.objects.create(user=user, business_category=category, subscription=subscription,
                                     **validated_data)

        # Получаем объекты для m2m связей
        format_obj_list = get_m2m_objects(data=formats_data, model_class=Formats, lookup_field='name')
        goal_obj_list = get_m2m_objects(data=goals_data, model_class=Goals, lookup_field='name')
        collab_with_obj_list = get_m2m_objects(data=collab_with_data, model_class=Category, lookup_field='name')

        # Добавляем связи с этими объектами
        brand.formats.add(*format_obj_list)
        brand.goal.add(*goal_obj_list)
        brand.collab_with.add(*collab_with_obj_list)

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
