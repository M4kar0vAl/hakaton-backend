from django.test import override_settings, TransactionTestCase, tag
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.chat.factories import (
    RoomAsyncFactory,
    MessageAsyncFactory
)
from core.apps.chat.models import Room
from core.apps.payments.factories import SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import join_room, get_user_communicator, websocket_connect


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    },
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
@tag('slow', 'chats')
class RoomConsumerGetSupportRoomTestCase(TransactionTestCase, RoomConsumerActionsMixin):

    def setUp(self):
        self.user1, self.user2 = UserFactory.create_batch(2, has_sub=True)

    async def test_get_support_room_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        await RoomAsyncFactory(participants=[user_wo_active_sub])
        sub = await SubscriptionAsyncFactory(brand__user=user_wo_active_sub)  # create active sub

        communicator = get_user_communicator(user_wo_active_sub)

        # connect with active sub
        async with websocket_connect(communicator):
            # make sub inactive
            sub.is_active = False
            await sub.asave()

            response = await self.get_support_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

    async def test_get_support_room(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.user1])
        msg = await MessageAsyncFactory(user=self.user1, room=room)

        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            response = await self.get_support_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        data = response['data']

        self.assertEqual(data['id'], room.pk)
        self.assertFalse(data['interlocutors'])
        self.assertEqual(data['last_message']['id'], msg.pk)

    async def test_get_support_room_if_does_not_exist(self):
        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            response = await self.get_support_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_201_CREATED)

        data = response['data']

        try:
            room = await Room.objects.prefetch_related('participants').aget(id=data['id'])
        except Room.DoesNotExist:
            room = None

        self.assertIsNotNone(room)
        self.assertEqual(room.type, Room.SUPPORT)
        self.assertFalse(data['interlocutors'])
        self.assertIsNone(data['last_message'])

        participants = room.participants.all()

        self.assertEqual(len(participants), 1)
        self.assertEqual(participants[0].pk, self.user1.pk)

    async def test_get_support_room_if_in_room(self):
        room1 = await RoomAsyncFactory(type=Room.MATCH, participants=[self.user1, self.user2])
        support_room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.user1])

        communicator = get_user_communicator(self.user1)

        async with join_room(communicator, room1.pk, connect=True):
            response = await self.get_support_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        data = response['data']
        self.assertEqual(data['id'], support_room.pk)
        self.assertFalse(data['interlocutors'])

    async def test_get_support_room_last_message_includes_attachments(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.user1])
        message = await MessageAsyncFactory(user=self.user1, room=room, has_attachments=True)
        attachments_ids = [pk async for pk in message.attachments.values_list('pk', flat=True).aiterator()]

        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            response = await self.get_support_room(communicator)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        last_message = response['data']['last_message']
        self.assertTrue('attachments' in last_message)

        response_attachments_ids = [a['id'] for a in last_message['attachments']]
        self.assertEqual(response_attachments_ids, attachments_ids)
