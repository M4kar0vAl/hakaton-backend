import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

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
