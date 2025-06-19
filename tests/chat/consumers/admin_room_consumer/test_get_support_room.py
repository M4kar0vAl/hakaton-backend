from django.test import tag, TransactionTestCase, override_settings
from rest_framework import status

from core.apps.accounts.factories import UserFactory
from core.apps.chat.consumers import AdminRoomConsumer
from core.apps.chat.factories import MessageAsyncFactory, RoomAsyncFactory
from core.apps.chat.models import Room
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import join_room, get_websocket_communicator_for_user


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerGetSupportRoomTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):
    serialized_rollback = True

    def setUp(self):
        self.admin_user = UserFactory(admin=True)

        self.path = 'ws/admin-chat/'
        self.accepted_protocol = 'admin-chat'

    async def test_get_support_room(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.admin_user])
        msg = await MessageAsyncFactory(user=self.admin_user, room=room)

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.get_support_room(communicator)
        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        data = response['data']
        self.assertEqual(data['id'], room.pk)
        self.assertFalse(data['interlocutors'])
        self.assertEqual(data['last_message']['id'], msg.pk)

        await communicator.disconnect()

    async def test_get_support_room_if_in_room(self):
        room = await RoomAsyncFactory(type=Room.MATCH)
        support_room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.admin_user])

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            response = await self.get_support_room(communicator)
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            data = response['data']
            self.assertEqual(data['id'], support_room.pk)
            self.assertFalse(data['interlocutors'])
            self.assertIsNone(data['last_message'])

        await communicator.disconnect()

    async def test_get_support_room_if_does_not_exist(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.get_support_room(communicator)
        self.assertEqual(response['response_status'], status.HTTP_201_CREATED)

        data = response['data']
        self.assertFalse(data['interlocutors'])
        self.assertIsNone(data['last_message'])

        try:
            room = await Room.objects.prefetch_related('participants').aget(id=data['id'])
        except Room.DoesNotExist:
            room = None

        self.assertIsNotNone(room)

        participants = room.participants.all()
        self.assertEqual(len(participants), 1)
        self.assertEqual(participants[0].pk, self.admin_user.pk)

        await communicator.disconnect()

    async def test_get_support_room_last_message_includes_attachments(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.admin_user])
        message = await MessageAsyncFactory(user=self.admin_user, room=room, has_attachments=True, attachments__file='')
        attachments_ids = [pk async for pk in message.attachments.values_list('pk', flat=True).aiterator()]

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.get_support_room(communicator)
        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        last_message = response['data']['last_message']
        self.assertTrue('attachments' in last_message)

        response_attachments_ids = [a['id'] for a in last_message['attachments']]
        self.assertEqual(response_attachments_ids, attachments_ids)

        await communicator.disconnect()
