from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    date_joined = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(default=True, label='Активирован')

    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'date_joined', 'is_active', 'is_staff']
