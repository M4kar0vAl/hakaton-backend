import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    phone = '+79993332211'
    fullname = 'Юзеров Юзер Юзерович'
    password = 'Pass!234'
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)

        return manager.create_user(*args, **kwargs)


class StaffUserFactory(UserFactory):
    email = factory.Sequence(lambda n: f'staff{n}@example.com')
    fullname = 'Стаффов Стафф Стаффович'
    is_staff = True


class AdminUserFactory(UserFactory):
    email = factory.Sequence(lambda n: f'admin{n}@example.com')
    fullname = 'Админов Админ Админович'

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)

        return manager.create_superuser(*args, **kwargs)
