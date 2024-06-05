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
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'phone',
        ]


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

