from datetime import timedelta
from random import randint

import factory
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from factory.django import DjangoModelFactory

from core.apps.brand.factories import BrandShortFactory
from core.apps.payments.models import Tariff, PromoCode, GiftPromoCode, Subscription


class TariffFactory(DjangoModelFactory):
    class Meta:
        model = Tariff
        django_get_or_create = ('name',)

    class Params:
        trial = factory.Trait(
            name='Trial',
            cost=0,
            duration=timedelta(days=14)
        )
        lite = factory.Trait(
            name='Lite Match',
            cost=6000,
            duration=timedelta(days=3 * 30)
        )
        business = factory.Trait(
            name='Business Match',
            cost=15000,
            duration=timedelta(days=3 * 30)
        )

    name = factory.Sequence(lambda n: f'Tariff {n}')
    cost = factory.LazyFunction(lambda: randint(1000, 15000))
    duration = factory.LazyFunction(lambda: timedelta(days=3 * 30))


class PromoCodeFactory(DjangoModelFactory):
    class Meta:
        model = PromoCode
        django_get_or_create = ('code',)

    class Params:
        expired = False

    code = factory.Sequence(lambda n: f'Promo Code {n}')
    discount = factory.LazyFunction(lambda: randint(0, 100))
    expires_at = factory.Maybe(
        'expired',
        yes_declaration=factory.LazyFunction(lambda: timezone.now() - relativedelta(hours=1)),
        no_declaration=factory.LazyFunction(lambda: timezone.now() + relativedelta(months=1))
    )


class GiftPromoCodeFactory(DjangoModelFactory):
    class Meta:
        model = GiftPromoCode
        django_get_or_create = ('code',)

    class Params:
        has_promocode = False
        expired = False

    code = factory.Faker('uuid4', cast_to=None)
    tariff = factory.SubFactory(TariffFactory, business=True)
    expires_at = factory.Maybe(
        'expired',
        yes_declaration=factory.LazyFunction(lambda: timezone.now() - relativedelta(days=1)),
        no_declaration=factory.LazyFunction(lambda: timezone.now() + relativedelta(months=6))
    )
    giver = factory.SubFactory(BrandShortFactory)
    is_used = False
    promocode = factory.Maybe(
        'has_promocode',
        yes_declaration=factory.SubFactory(PromoCodeFactory),
        no_declaration=None
    )


class SubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = Subscription

    class Params:
        expired = False
        has_promocode = False
        is_upgraded = factory.Trait(
            upgraded_from=factory.SubFactory(TariffFactory, lite=True),
            upgraded_at=factory.LazyAttribute(lambda o: o.start_date + timedelta(days=10))
        )
        is_gifted = factory.Trait(
            gift_promocode = factory.SubFactory(GiftPromoCodeFactory, is_used=True),
            tariff = factory.SubFactory(TariffFactory, business=True)
        )

    brand = factory.SubFactory(BrandShortFactory)
    tariff = factory.SubFactory(TariffFactory, lite=True)
    start_date = timezone.now()
    end_date = factory.Maybe(
        'expired',
        yes_declaration=factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1)),
        no_declaration=factory.LazyAttribute(lambda o: o.start_date + o.tariff.get_duration_as_relativedelta())
    )
    is_active = True
    promocode = factory.Maybe(
        'has_promocode',
        yes_declaration=factory.SubFactory(PromoCodeFactory),
        no_declaration=None
    )
    upgraded_from = None
    upgraded_at = None
    gift_promocode = None
