from datetime import timedelta

import factory
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F
from factory import post_generation
from factory.django import DjangoModelFactory

from core.apps.accounts.models import PasswordRecoveryToken
from core.apps.accounts.utils import get_recovery_token_hash, get_recovery_token

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('email',)

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    phone = '+79993332211'
    fullname = 'Юзеров Юзер Юзерович'
    password = factory.django.Password('Pass!234')
    is_active = True


class StaffUserFactory(UserFactory):
    email = factory.Sequence(lambda n: f'staff{n}@example.com')
    fullname = 'Стаффов Стафф Стаффович'
    is_staff = True


class AdminUserFactory(StaffUserFactory):
    email = factory.Sequence(lambda n: f'admin{n}@example.com')
    fullname = 'Админов Админ Админович'
    is_superuser = True


class PasswordRecoveryTokenFactory(DjangoModelFactory):
    class Meta:
        model = PasswordRecoveryToken
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    token = factory.LazyFunction(lambda: get_recovery_token_hash(get_recovery_token()))


class PasswordRecoveryTokenExpiredFactory(PasswordRecoveryTokenFactory):
    @post_generation
    def created(self, create, extracted, **kwargs):
        # if obj was not created, does nothing
        if not create:
            return

        # if created was passed to the factory as a parameter,
        # sets object created value to that one
        if extracted:
            self.created = extracted
        # if token is already expired, does nothing
        elif self.is_expired:
            return
        # otherwise sets created such a way that token is expired now
        else:
            self.created = F('created') - timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
