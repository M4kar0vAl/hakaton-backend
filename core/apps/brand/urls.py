from rest_framework import routers

from core.apps.brand.api import BrandViewSet
from core.config import settings

router = routers.DefaultRouter()
router.register('brand', BrandViewSet, basename='brand')

urlpatterns = []

urlpatterns += router.urls
