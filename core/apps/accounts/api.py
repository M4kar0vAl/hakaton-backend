from django.contrib.auth import get_user_model
from rest_framework import viewsets, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.accounts.serializers import (
    CreateUserSerializer,
    UserSerializer,
    UpdateUserSerializer,
    PasswordResetSerializer,
    PasswordRecoverySerializer,
    PasswordRecoveryConfirmSerializer,

)

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


class PasswordRecoveryViewSet(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin
):
    serializer_class = PasswordRecoverySerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'confirm':
            return PasswordRecoveryConfirmSerializer

        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        # have not used raise_exception=True flag intentionally,
        # users SHOULD NOT know whether a user with the given email exists or not
        if serializer.is_valid():
            serializer.save()

        # return 200 status regardless of whether token was created and sent or not
        return Response(data=None, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_name='confirm')
    def confirm(self, request, *args, **kwargs):
        # Call update method in serializer to set new password for the user.
        # Instance doesn't matter, it's not used.
        serializer = self.get_serializer({}, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'response': 'Password successfully reset!'}, status=status.HTTP_200_OK)
