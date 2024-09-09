from django.urls import path, include
from rest_framework import routers

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from core.apps.accounts.api import UserViewSet, RequestPasswordRecoveryViewSet, RecoveryPasswordViewSet

router = routers.DefaultRouter()
router.register('users', UserViewSet, basename='users')

urlpatterns = [
    path('jwt/create/', TokenObtainPairView.as_view(), name='jwt_create'),
    path('jwt/refresh/', TokenRefreshView.as_view(), name='jwt_refresh'),

    path('password_recovery_request/', RequestPasswordRecoveryViewSet.as_view(), name='password_recovery_request'),
    path('recovery_password/<str:token>/', RecoveryPasswordViewSet.as_view(), name='recovery_password'),
]

urlpatterns += router.urls
