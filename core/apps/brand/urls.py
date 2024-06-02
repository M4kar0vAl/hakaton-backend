from django.conf.urls.static import static
from django.urls import path, include
from rest_framework import routers

from config import settings
from core.apps.brand.api import BrandViewSet

router = routers.DefaultRouter()
router.register('brands', BrandViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]

# Нужно чтобы изображения загруженные пользователями корректно отображались при DEBUG = True
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
