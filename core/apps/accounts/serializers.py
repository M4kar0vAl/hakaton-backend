import base64

from django.conf import settings
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers, exceptions

User = get_user_model()


class PasswordValidateMixin:
    def validate(self, attrs):
        user = User(**attrs)
        password = attrs.get('password')

        try:
            validate_password(password, user)
        except exceptions.ValidationError:
            raise serializers.ValidationError(
                {'password': 'Пароль слишком простой'}
            )

        return attrs


class CreateUserSerializer(
    PasswordValidateMixin,
    serializers.ModelSerializer
):
    password = serializers.CharField(style={"input_type": "password"}, write_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'phone',
            'password',
        ]

    def create(self, validated_data):
        try:
            user = self.perform_create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {'detail': 'Невозможно создать пользователя'}
            )
        return user

    def perform_create(self, validated_data):
        with transaction.atomic():
            validated_data['is_active'] = True
            user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    telegram_link = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'phone',
            'telegram_link',
        ]

    def get_telegram_link(self, obj):
        base_url = settings.BOT_URL
        user_id = str(obj.id)
        b64 = base64.b64encode(user_id.encode()).decode().rstrip('==')
        return f'{base_url}?start={b64}'


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        read_only_fields = ['id', 'email']
        fields = [
            'id',
            'email',
            'phone',
        ]


class PasswordResetSerializer(
    PasswordValidateMixin,
    serializers.Serializer,
):
    password = serializers.CharField()


class UserDecodeID(serializers.Serializer):
    user_id = serializers.CharField()

    def validate(self, attrs):
        try:
            user_code: str = attrs.get('user_id')
            b64_b: bytes = f'{user_code}=='.encode()
            user_id: int = int(base64.b64decode(b64_b).decode())
            self.user = User.objects.get(pk=user_id)
        except (UnicodeDecodeError, ValueError, User.DoesNotExist):
            raise exceptions.ValidationError(
                detail={'user_id': 'Некорректная ссылка'}
            )
        if self.user.is_staff:
            return attrs

        raise exceptions.ValidationError(
                detail='Этот бот предназначен для персонала W2W-Match'
            )


class UserTelegramID(UserDecodeID):
    telegram_id = serializers.IntegerField()

    def validate(self, attrs):
        return super().validate(attrs)
