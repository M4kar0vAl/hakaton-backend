from django.contrib.auth import get_user_model
from rest_framework import viewsets

from core.apps.accounts.serializers import UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
