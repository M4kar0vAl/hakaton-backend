from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),

    # api doc urls:
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # apps urls
    path('api/v1/', include('core.apps.brand.urls')),
    path('auth/', include('core.apps.accounts.urls')),
    path('api/v1/', include('core.apps.payments.urls')),
    path('api/v1/', include('core.apps.cities.urls')),
    path('api/v1/', include('core.apps.blacklist.urls')),
    path('api/v1/', include('core.apps.chat.urls')),
    path('api/v1/', include('core.apps.analytics.urls')),
    path('api/v1/', include('core.apps.articles.urls')),
]

# Нужно чтобы изображения загруженные пользователями корректно отображались при DEBUG = True
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
