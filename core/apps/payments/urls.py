from django.urls import path, include
from rest_framework import routers

from .api import PaymentViewSet

urlpatterns = [
    path('payments/', PaymentViewSet.as_view()),
]
