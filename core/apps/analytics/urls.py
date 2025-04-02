from rest_framework import routers

from core.apps.analytics.api import BrandActivityViewSet

router = routers.DefaultRouter()
router.register('analytics', BrandActivityViewSet, basename='analytics')

urlpatterns = []

urlpatterns += router.urls
