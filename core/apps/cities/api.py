from cities_light.models import City
from rest_framework import generics

from core.apps.cities.serializers import CitySerializer


class CitiesListApiView(generics.ListAPIView):
    serializer_class = CitySerializer
    queryset = City.objects.all()
