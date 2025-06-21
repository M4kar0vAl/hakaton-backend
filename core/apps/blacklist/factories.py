import factory
from factory.django import DjangoModelFactory

from core.apps.blacklist.models import BlackList
from core.apps.brand.factories import BrandShortFactory
from core.common.factories import factory_sync_to_async


class BlackListFactory(DjangoModelFactory):
    class Meta:
        model = BlackList
        django_get_or_create = ('initiator', 'blocked',)

    initiator = factory.SubFactory(BrandShortFactory)
    blocked = factory.SubFactory(BrandShortFactory)


BlackListAsyncFactory = factory_sync_to_async(BlackListFactory)
