from rest_framework import routers

from core.apps.blacklist.api import BlacklistViewSet

router = routers.DefaultRouter()
router.register('blacklist', BlacklistViewSet, basename='blacklist')

urlpatterns = []

urlpatterns += router.urls
