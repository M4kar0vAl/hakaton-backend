from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction, DatabaseError
from rest_framework import serializers, exceptions

from core.apps.accounts.models import PasswordRecoveryToken
from core.apps.accounts.tasks import send_password_recovery_email
from core.apps.accounts.utils import get_recovery_token, get_recovery_token_hash

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
            'fullname',
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
            'fullname',
            'email',
            'phone',
            'brand',
        ]


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        read_only_fields = ['id', 'email']
        fields = [
            'id',
            'fullname',
            'email',
            'phone',
        ]


class PasswordResetSerializer(
    PasswordValidateMixin,
    serializers.Serializer,
):
    password = serializers.CharField()


class PasswordRecoverySerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get('email')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('User with the given email does not exist!')

        if PasswordRecoveryToken.objects.filter(user=user).exists():
            raise serializers.ValidationError('Token was already created for the given user')

        attrs['user'] = user  # set user to attrs to avoid refetching it from db in self.create

        return attrs

    def create(self, validated_data):
        user = validated_data.get('user')
        token = get_recovery_token()
        hashed_token = get_recovery_token_hash(token)

        try:
            with transaction.atomic():
                instance = PasswordRecoveryToken.objects.create(user=user, token=hashed_token)
                send_password_recovery_email.delay_on_commit(user.email, token)
        except DatabaseError:
            raise serializers.ValidationError('Failed to perform action! Please, try again later!')

        return instance


class PasswordRecoveryConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=32)
    new_password = serializers.CharField(style={"input_type": "password"}, write_only=True)

    def validate(self, attrs):
        # 'validate' method runs AFTER field validation e.g. 'validate_token'.
        # So at this point self.context is already populated with 'recovery_token'
        user = self.context.get('recovery_token').user
        new_password = attrs.get('new_password')

        # validating password here, because it uses 'user' object to perform validation
        try:
            validate_password(new_password, user)
        except exceptions.ValidationError:
            raise serializers.ValidationError({'new_password': 'Password is too simple!'})

        return attrs

    def validate_token(self, token):
        token_hash = get_recovery_token_hash(token)

        try:
            recovery_token = PasswordRecoveryToken.objects.get(token=token_hash)
        except PasswordRecoveryToken.DoesNotExist:
            raise serializers.ValidationError('Invalid token!')

        if recovery_token.is_expired:
            raise serializers.ValidationError('Token expired!')

        self.context['recovery_token'] = recovery_token

        return token

    def update(self, instance, validated_data):
        recovery_token = self.context.get('recovery_token')
        user = recovery_token.user
        new_password = validated_data.get('new_password')

        try:
            with transaction.atomic():
                user.set_password(new_password)
                user.save()
                recovery_token.delete()
        except DatabaseError:
            serializers.ValidationError('Failed to perform action. Please, try again later!')

        return instance
