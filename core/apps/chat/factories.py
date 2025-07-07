from random import randint

import factory
from django.conf import settings
from factory import post_generation
from factory.django import DjangoModelFactory

from core.apps.accounts.factories import UserFactory
from core.apps.chat.models import Room, Message, MessageAttachment, RoomFavorites
from core.common.factories import factory_sync_to_async


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


RoomAsyncFactory = factory_sync_to_async(RoomFactory)


class MessageAttachmentFactory(DjangoModelFactory):
    class Meta:
        model = MessageAttachment

    message = None
    file = factory.django.FileField()

    @post_generation
    def created_at(self, create, extracted, **kwargs):
        # if obj is not created, does nothing
        if not create:
            return

        # if the concrete value is passed, use it
        if extracted:
            self.created = extracted

    @post_generation
    def expired(self, create, extracted, **kwargs):
        """
        Used to make an expired attachment.
        To make an expired attachment pass expired=True when calling factory
        """
        if not create:
            return

        if extracted:
            self.created_at -= settings.MESSAGE_ATTACHMENT_DANGLING_LIFE_TIME


MessageAttachmentAsyncFactory = factory_sync_to_async(MessageAttachmentFactory)


class MessageFactory(DjangoModelFactory):
    class Meta:
        model = Message

    class Params:
        has_attachments = False

    text = factory.Faker('paragraph')
    user = factory.SubFactory(UserFactory)
    room = factory.SubFactory(RoomFactory)
    attachments = factory.Maybe(
        'has_attachments',
        yes_declaration=factory.RelatedFactoryList(
            MessageAttachmentFactory, factory_related_name='message', size=lambda: randint(1, 3)
        ),
        no_declaration=None
    )


MessageAsyncFactory = factory_sync_to_async(MessageFactory)


class RoomFavoritesFactory(DjangoModelFactory):
    class Meta:
        model = RoomFavorites
        django_get_or_create = ('user', 'room',)

    user = factory.SubFactory(UserFactory)
    room = factory.SubFactory(RoomFactory)
