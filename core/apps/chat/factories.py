from random import randint

import factory
from django.conf import settings
from django.db.models import F
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


class RoomMatchFactory(RoomFactory):
    type = Room.MATCH


RoomMatchAsyncFactory = factory_sync_to_async(RoomMatchFactory)


class RoomInstantFactory(RoomFactory):
    type = Room.INSTANT


RoomInstantAsyncFactory = factory_sync_to_async(RoomInstantFactory)


class RoomSupportFactory(RoomFactory):
    type = Room.SUPPORT


RoomSupportAsyncFactory = factory_sync_to_async(RoomSupportFactory)


class MessageAttachmentFactory(DjangoModelFactory):
    class Meta:
        model = MessageAttachment

    message = None
    file = factory.django.FileField()


MessageAttachmentAsyncFactory = factory_sync_to_async(MessageAttachmentFactory)


class MessageAttachmentExpiredFactory(MessageAttachmentFactory):
    @factory.post_generation
    def created_at(self, create, extracted, **kwargs):
        if not create:
            return

        self.created_at = F('created_at') - settings.MESSAGE_ATTACHMENT_DANGLING_LIFE_TIME


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
