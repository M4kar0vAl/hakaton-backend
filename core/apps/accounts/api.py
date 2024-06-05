from django.contrib.auth import get_user_model

from rest_framework import viewsets, mixins, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.accounts.serializers import (
    CreateUserSerializer,
    UserSerializer,
    UpdateUserSerializer,
    PasswordResetSerializer,
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

    @action(['get', 'patch', 'delete'], detail=False, url_name='me')
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
        elif request.method == 'DELETE':
            user.delete()
            return Response(status=204)

    @action(['post'], detail=False, url_name='password_reset')
    def password_reset(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data['password']
        user = request.user
        user.set_password(new_password)
        user.save()
        return Response(data=UserSerializer(instance=user).data, status=200)
