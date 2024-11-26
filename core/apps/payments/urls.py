from rest_framework import routers

from core.apps.payments.api import TariffViewSet

router = routers.DefaultRouter()
router.register('tariffs', TariffViewSet, basename='tariffs')

urlpatterns = []

urlpatterns += router.urls
