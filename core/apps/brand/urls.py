from django.conf.urls.static import static
from django.urls import path

from config import settings

urlpatterns = [

]

# TODO убрать в проде
# Нужно чтобы изображения загруженные пользователями корректно отображались при DEBUG = True
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
