from django.urls import path
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from core.apps.accounts.api import (
    UserViewSet,
    PasswordRecoveryViewSet
)

router = routers.DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('password_recovery', PasswordRecoveryViewSet, basename='password_recovery')

urlpatterns = [
    path('jwt/create/', TokenObtainPairView.as_view(), name='jwt_create'),
    path('jwt/refresh/', TokenRefreshView.as_view(), name='jwt_refresh'),
]

urlpatterns += router.urls
