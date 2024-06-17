from django.conf.urls.static import static
from rest_framework import routers

from core.apps.brand.api import BrandViewSet
from core.config import settings

router = routers.DefaultRouter()
router.register('brand', BrandViewSet)

urlpatterns = []

urlpatterns += router.urls

# Нужно чтобы изображения загруженные пользователями корректно отображались при DEBUG = True
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
