import factory
from cities_light.models import City, Country
from factory.django import DjangoModelFactory


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = Country

    name = factory.Sequence(lambda n: f'Country {n}')
    continent = factory.Iterator(['OC', 'EU', 'AF', 'NA', 'AN', 'SA', 'AS'])


class CityFactory(DjangoModelFactory):
    class Meta:
        model = City

    name = factory.Sequence(lambda n: f'City {n}')
    country = factory.SubFactory(CountryFactory)
