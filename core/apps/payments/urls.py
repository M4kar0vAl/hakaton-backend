from django.urls import path, include
from rest_framework import routers

from .api import PaymentViewSet
from rest_framework import routers


router = routers.DefaultRouter()
router.register('payment', PaymentViewSet, basename='payments')

urlpatterns = []

urlpatterns += router.urls
