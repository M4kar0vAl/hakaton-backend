from django.urls import path
from rest_framework import routers

from core.apps.payments.api import TariffViewSet, PromocodeRetrieveApiView

router = routers.DefaultRouter()
router.register('tariffs', TariffViewSet, basename='tariffs')

urlpatterns = [
    path('promocodes/<str:code>/', PromocodeRetrieveApiView.as_view(), name='promocode-detail')
]

urlpatterns += router.urls
