from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework import viewsets, mixins, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.accounts.models import PasswordRecovery
from core.apps.accounts.serializers import (
    CreateUserSerializer,
    UserSerializer,
    UpdateUserSerializer,
    PasswordResetSerializer,
    RequestPasswordRecoverySerializer,
    RecoveryPasswordSerializer,
)
from core.apps.accounts.utils import send_password_recovery_email

User = get_user_model()


class UserViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateUserSerializer
        elif self.action == 'me':
            if self.request.method == 'GET':
                return UserSerializer
            elif self.request.method == 'PATCH':
                return UpdateUserSerializer
        elif self.action == 'password_reset':
            return PasswordResetSerializer

        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny(), ]

        return super().get_permissions()

    @action(['get', 'patch'], detail=False, url_name='me')
    def me(self, request, *args, **kwargs):
        user = self.request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(data=serializer.data, status=200)
        elif request.method == 'PATCH':
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(data=serializer.data, status=200)

    @action(['post'], detail=False, url_name='password_reset')
    def password_reset(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data['password']
        user = request.user
        user.set_password(new_password)
        user.save()
        return Response(data=UserSerializer(instance=user).data, status=200)


class RequestPasswordRecoveryViewSet(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RequestPasswordRecoverySerializer

    def post(self, request):
        serializer = RequestPasswordRecoverySerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.filter(email__iexact=email).first()

            if user:
                token = PasswordResetTokenGenerator().make_token(user)
                reset = PasswordRecovery(email=email, token=token)
                reset.save()

                # TODO send mail
                send_password_recovery_email(email, token, request.get_host())

                return Response({"success": "Password recovery link sent"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "User with credentials not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecoveryPasswordViewSet(generics.GenericAPIView):
    permissions_classes = [permissions.AllowAny]
    serializer_class = RecoveryPasswordSerializer

    def post(self, request, token):
        serializer = RecoveryPasswordSerializer(data=request.data)
        if serializer.is_valid():
            new_password = serializer.validated_data['new_password']
            confirm_password = serializer.validated_data['confirm_password']

            if new_password != confirm_password:
                return Response({"error": "Passwords don't match"}, status=status.HTTP_400_BAD_REQUEST)

            reset_obj = PasswordRecovery.objects.filter(token=token).first()

            if not reset_obj:
                return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.filter(email=reset_obj.email).first()

            if not user:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            user.set_password(new_password)
            user.save()
            reset_obj.delete()
            return Response({"success": "Password changed"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
