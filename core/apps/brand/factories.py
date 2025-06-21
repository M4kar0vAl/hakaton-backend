from random import randint

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from core.apps.accounts.factories import UserFactory
from core.apps.brand.models import (
    Brand,
    Category,
    TargetAudience,
    Tag,
    Format,
    Goal,
    Age,
    Gender,
    GEO,
    Blog,
    BusinessGroup,
    ProductPhoto,
    GalleryPhoto, Match, Collaboration
)
from core.apps.chat.factories import RoomFactory
from core.apps.chat.models import Room
from core.apps.cities.factories import CityFactory
from core.common.factories import factory_sync_to_async


class GenderDistributedTAModelFactory(DjangoModelFactory):
    class Meta:
        abstract = True

    men = factory.LazyFunction(lambda: randint(0, 100))
    women = factory.LazyFunction(lambda: randint(0, 100))


class AgeFactory(GenderDistributedTAModelFactory):
    class Meta:
        model = Age


class GenderFactory(GenderDistributedTAModelFactory):
    class Meta:
        model = Gender

    women = factory.LazyAttribute(lambda o: 100 - o.men)


class GeoFactory(DjangoModelFactory):
    class Meta:
        model = GEO

    city = factory.SubFactory(CityFactory)
    people_percentage = factory.LazyFunction(lambda: randint(1, 100))
    target_audience = None


class TargetAudienceFactory(DjangoModelFactory):
    class Meta:
        model = TargetAudience

    age = factory.SubFactory(AgeFactory)
    gender = factory.SubFactory(GenderFactory)
    income = factory.LazyFunction(lambda: randint(50000, 1000000))
    geos = factory.RelatedFactoryList(
        GeoFactory, factory_related_name='target_audience', size=lambda: randint(1, 3)
    )


class BlogFactory(DjangoModelFactory):
    class Meta:
        model = Blog

    brand = None
    blog = factory.Faker('url')


class BusinessGroupFactory(DjangoModelFactory):
    class Meta:
        model = BusinessGroup

    brand = None
    name = factory.Sequence(lambda n: f'Business Group {n}')


class BrandM2MAbstractFactory(DjangoModelFactory):
    class Meta:
        abstract = True

    name = None
    is_other = False


class TagFactory(BrandM2MAbstractFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f'Tag {n}')


class CategoryFactory(BrandM2MAbstractFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f'Category {n}')


class FormatFactory(BrandM2MAbstractFactory):
    class Meta:
        model = Format

    name = factory.Sequence(lambda n: f'Format {n}')


class GoalFactory(BrandM2MAbstractFactory):
    class Meta:
        model = Goal

    name = factory.Sequence(lambda n: f'Goal {n}')


class ProductPhotoFactory(DjangoModelFactory):
    class Meta:
        model = ProductPhoto

    brand = None
    format = factory.Iterator(ProductPhoto.FORMAT_CHOICES.keys())
    image = factory.django.ImageField()


class GalleryPhotoFactory(DjangoModelFactory):
    class Meta:
        model = GalleryPhoto

    brand = None
    image = factory.django.ImageField()


class BrandPartOnePostGenerationFactory(DjangoModelFactory):
    class Meta:
        abstract = True

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        self.tags.add(*extracted)


class BrandPartTwoPostGenerationFactory(DjangoModelFactory):
    class Meta:
        abstract = True

    @factory.post_generation
    def formats(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        self.formats.add(*extracted)

    @factory.post_generation
    def goals(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        self.goals.add(*extracted)

    @factory.post_generation
    def categories_of_interest(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        self.categories_of_interest.add(*extracted)


class BrandShortBaseFactory(DjangoModelFactory):
    class Meta:
        abstract = True

    user = factory.SubFactory(UserFactory)
    city = factory.SubFactory(CityFactory)
    tg_nickname = '@example'
    name = factory.Sequence(lambda n: f'Brand {n}')
    position = factory.Faker('sentence', nb_words=4)
    category = factory.SubFactory(CategoryFactory)
    subs_count = factory.LazyFunction(lambda: randint(1, 10_000_000))
    avg_bill = factory.LazyFunction(lambda: randint(1, 10_000_000))
    uniqueness = factory.Faker('paragraph')
    logo = ''
    photo = ''


class BrandShortFactory(
    BrandShortBaseFactory,
    BrandPartOnePostGenerationFactory,
    BrandPartTwoPostGenerationFactory
):
    class Meta:
        model = Brand
        django_get_or_create = ('user',)


BrandShortAsyncFactory = factory_sync_to_async(BrandShortFactory)


class BrandPartOneFactory(
    BrandShortBaseFactory,
    BrandPartOnePostGenerationFactory
):
    class Meta:
        model = Brand
        django_get_or_create = ('user',)

    blogs = factory.RelatedFactoryList(BlogFactory, factory_related_name='brand', size=lambda: randint(1, 3))
    inst_url = factory.Faker('url')
    vk_url = factory.Faker('url')
    tg_url = factory.Faker('url')
    wb_url = factory.Faker('url')
    lamoda_url = factory.Faker('url')
    site_url = factory.Faker('url')
    logo = factory.django.ImageField()
    photo = factory.django.ImageField()
    product_photos = factory.RelatedFactoryList(
        ProductPhotoFactory, factory_related_name='brand', size=lambda: randint(2, 4)
    )


class BrandFactory(
    BrandPartOneFactory,
    BrandPartTwoPostGenerationFactory
):
    business_groups = factory.RelatedFactoryList(
        BusinessGroupFactory, factory_related_name='brand', size=lambda: randint(1, 3)
    )
    gallery_photos = factory.RelatedFactoryList(
        GalleryPhotoFactory, factory_related_name='brand', size=lambda: randint(1, 3)
    )
    mission_statement = factory.Faker('paragraph')
    offline_space = factory.Faker('address')
    problem_solving = factory.Faker('paragraph')
    target_audience = factory.SubFactory(TargetAudienceFactory)


class MatchFactory(DjangoModelFactory):
    class Meta:
        model = Match
        django_get_or_create = ('initiator', 'target',)

    class Params:
        like = factory.Trait(
            is_match=False,
            match_at=None,
            room=None,
        )
        instant_coop = factory.Trait(
            like=True,
            room=factory.SubFactory(RoomFactory, type=Room.INSTANT),
        )

    initiator = factory.SubFactory(BrandShortFactory)
    target = factory.SubFactory(BrandShortFactory)
    is_match = True
    match_at = factory.LazyFunction(lambda: timezone.now())
    room = factory.SubFactory(RoomFactory, type=Room.MATCH)

    @factory.post_generation
    def like_at(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        self.like_at = extracted

    @factory.post_generation
    def room_participants(self, create, extracted, **kwargs):
        if not create:
            return

        if self.room is not None:
            self.room.participants.add(self.initiator.user, self.target.user)


MatchAsyncFactory = factory_sync_to_async(MatchFactory)


class CollaborationFactory(DjangoModelFactory):
    class Meta:
        model = Collaboration
        django_get_or_create = ('reporter', 'collab_with',)

    class Params:
        is_reporter_match_initiator = True

    reporter = factory.SubFactory(BrandShortFactory)
    collab_with = factory.SubFactory(BrandShortFactory)
    match = factory.Maybe(
        'is_reporter_match_initiator',
        yes_declaration=factory.SubFactory(
            MatchFactory,
            initiator=factory.SelfAttribute('..reporter'),
            target=factory.SelfAttribute('..collab_with')
        ),
        no_declaration=factory.SubFactory(
            MatchFactory,
            initiator=factory.SelfAttribute('..collab_with'),
            target=factory.SelfAttribute('..reporter')
        )
    )
    success_assessment = factory.LazyFunction(lambda: randint(1, 10))
    success_reason = factory.Faker('paragraph', nb_sentences=5)
    to_improve = factory.Faker('paragraph', nb_sentences=5)
    subs_received = factory.LazyFunction(lambda: randint(1, 1_000_000))
    leads_received = factory.LazyFunction(lambda: randint(1, 1_000_000))
    sales_growth = factory.Faker('paragraph', nb_sentences=1)
    audience_reach = factory.LazyFunction(lambda: randint(1, 1_000_000))
    bill_change = factory.Faker('paragraph', nb_sentences=1)
    new_offers = factory.LazyFunction(lambda: bool(randint(0, 1)))
    new_offers_comment = factory.Faker('paragraph', nb_sentences=5)
    perception_change = factory.LazyFunction(lambda: bool(randint(0, 1)))
    brand_compliance = factory.LazyFunction(lambda: randint(1, 10))
    platform_help = factory.LazyFunction(lambda: randint(1, 5))
    difficulties = factory.LazyFunction(lambda: bool(randint(0, 1)))
    difficulties_comment = factory.Faker('paragraph', nb_sentences=5)

    @factory.post_generation
    def created_at(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        self.created_at = extracted
