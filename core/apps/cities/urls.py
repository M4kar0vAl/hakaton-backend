from django.urls import path

from core.apps.cities.api import CitiesListApiView

urlpatterns = [
    path('cities/', CitiesListApiView.as_view(), name='cities')
]
