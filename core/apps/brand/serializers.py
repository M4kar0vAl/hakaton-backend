from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response

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
    user_id = UserSerializer()
    business_category = CategorySerializer()
    formats = FormatSerializer(many=True)
    goal = GoalSerializer(many=True)
    collab_with = CategorySerializer(many=True)
    subscription = SubscriptionSerializer()

    class Meta:
        model = Brand
        fields = [
            'id', 'user_id', 'published', 'fi', 'birth_date', 'tg_nickname', 'brand_name_pos', 'business_category',
            'inst_brand_url', 'inst_profile_url', 'tg_brand_url', 'brand_site_url', 'topics', 'subs_count', 'avg_bill',
            'values', 'target_audience', 'territory', 'formats', 'goal', 'collab_with', 'logo', 'photo',
            'product_photo', 'subscription', 'sub_expire'
        ]

    def create(self, validated_data):
        """
        Метод для создания бренда. Здесь обрабатываются поля-внешние ключи
        """
        # СНАЧАЛА РАБОТАЕМ С ONE-TO-ONE И FK

        # Получаем введенные данные пользователя
        user_data = validated_data.pop('user_id')

        # Пытаемся получить пользователя из БД (возможно будет нужно для предрегистрации!)
        try:
            user = User.objects.get(email=user_data.get('email'))
        except User.DoesNotExist:
            user = None

        # Если пользователя нет - создаем
        if not user:
            user = User.objects.create(**user_data)

        # Получаем данные по категории
        category_data = validated_data.pop('business_category')

        # Пытаемся получить категорию из БД.
        # Если не находим - возвращаем 404 ответ, т.к. категории строго предопределены
        try:
            category = Category.objects.get(category_data.get('name'))
        except Category.DoesNotExist:
            return Response({'error': 'Category does not exist'}, status=status.HTTP_404_NOT_FOUND)

        # Получаем данные по подписке
        subscription_data = validated_data.pop('subscription')

        # Пытаемся получить подписку из БД.
        # Если не находим - возвращаем 404 ответ, т.к. подписки строго предопределены
        try:
            subscription = Subscription.objects.get(**subscription_data)
        except Subscription.DoesNotExist:
            return Response({'error': 'Subscription does not exist'}, status=status.HTTP_404_NOT_FOUND)

        # ЗАТЕМ ПЕРЕХОДИМ К MANY-TO-MANY

        # Получаем данные по m2m полям
        formats_data = validated_data.pop('formats')
        goals_data = validated_data.pop('goal')
        collab_with_data = validated_data.pop('collab_with')

        # Создаем объект бренда в БД на основе имеющихся данных (без many-to-many полей)
        brand = Brand.objects.create(user_id=user, business_category=category, subscription=subscription,
                                     **validated_data)

        # Проходим циклами по данным всех m2m полей и добавляем бренду связь с каждым из них

        for format_data in formats_data:
            format = Formats.objects.get(**format_data)
            brand.formats.add(format)

        for goal_data in goals_data:
            goal = Goals.objects.get(**goal_data)
            brand.goal.add(goal)

        for collab_with in collab_with_data:
            collab_with = Category.objects.get(**collab_with)
            brand.collab_with.add(collab_with)

        return brand
