from datetime import timedelta

import factory
from django.conf import settings
from django.contrib.auth import get_user_model
from factory import post_generation
from factory.django import DjangoModelFactory

from core.apps.accounts.models import PasswordRecoveryToken
from core.apps.accounts.utils import get_recovery_token_hash, get_recovery_token
from core.common.factories import factory_sync_to_async

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('email',)

    class Params:
        staff = factory.Trait(
            email=factory.Sequence(lambda n: f'staff{n}@example.com'),
            is_staff=True,
        )
        admin = factory.Trait(
            staff=True,
            email=factory.Sequence(lambda n: f'admin{n}@example.com'),
            is_superuser=True,
        )
        has_sub = factory.Trait(
            brand=factory.RelatedFactory(
                'core.apps.brand.factories.BrandShortFactory', factory_related_name='user', has_sub=True
            )
        )

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    phone = '+79993332211'
    fullname = factory.Faker('name')
    password = factory.django.Password('Pass!234')
    is_active = True


UserAsyncFactory = factory_sync_to_async(UserFactory)


class PasswordRecoveryTokenFactory(DjangoModelFactory):
    class Meta:
        model = PasswordRecoveryToken
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    token = factory.LazyFunction(lambda: get_recovery_token_hash(get_recovery_token()))

    @post_generation
    def created(self, create, extracted, **kwargs):
        # if obj is not created, does nothing
        if not create:
            return

        # if the concrete value is passed, use it
        if extracted:
            self.created = extracted

    @post_generation
    def expired(self, create, extracted, **kwargs):
        """
        Used to make an expired token.
        To make an expired token pass expired=True when calling factory
        """
        if not create:
            return

        if extracted:
            self.created -= timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
