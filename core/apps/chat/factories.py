from random import randint

import factory
from factory.django import DjangoModelFactory

from core.apps.accounts.factories import UserFactory
from core.apps.chat.models import Room, Message, MessageAttachment, RoomFavorites


class MessageAttachmentFactory(DjangoModelFactory):
    class Meta:
        model = MessageAttachment

    message = None
    file = factory.django.FileField()


class MessageFactory(DjangoModelFactory):
    class Meta:
        model = Message

    text = factory.Faker('paragraph')
    user = factory.SubFactory(UserFactory)
    room = factory.SubFactory('core.apps.chat.factories.RoomFactory')


class MessageWithAttachmentsFactory(MessageFactory):
    attachments = factory.RelatedFactoryList(
        MessageAttachmentFactory, factory_related_name='message', size=lambda: randint(1, 3)
    )


class RoomFactory(DjangoModelFactory):
    class Meta:
        model = Room

    type = factory.Iterator(Room.TYPE_CHOICES.keys())

    @factory.post_generation
    def participants(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        if len(extracted) > 2:
            raise ValueError('Room cannot have more than two participants.')

        self.participants.add(*extracted)


class RoomMatchFactory(RoomFactory):
    type = Room.MATCH


class RoomInstantFactory(RoomFactory):
    type = Room.INSTANT


class RoomSupportFactory(RoomFactory):
    type = Room.SUPPORT


class RoomFavoritesFactory(DjangoModelFactory):
    class Meta:
        model = RoomFavorites
        django_get_or_create = ('user', 'room',)

    user = factory.SubFactory(UserFactory)
    room = factory.SubFactory(RoomFactory)
