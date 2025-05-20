from django.contrib.auth import get_user_model
from django.test import tag, TransactionTestCase, override_settings
from rest_framework import status

from core.apps.chat.consumers import AdminRoomConsumer
from core.apps.chat.models import Room, Message, MessageAttachment
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import join_room, get_websocket_communicator_for_user

User = get_user_model()


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
        self.admin_user = User.objects.create_superuser(
            email=f'admin_user@example.com',
            phone='+79993332211',
            fullname='Админов Админ Админович',
            password='Pass!234',
            is_active=True
        )

        self.path = 'ws/admin-chat/'
        self.accepted_protocol = 'admin-chat'

    async def test_get_support_room(self):
        room = await Room.objects.acreate(type=Room.SUPPORT)

        await room.participants.aset([self.admin_user])

        msg = await Message.objects.acreate(
            text='test',
            user=self.admin_user,
            room=room
        )

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

        room_id = response['data']['id']
        interlocutors = response['data']['interlocutors']
        last_message = response['data']['last_message']

        self.assertEqual(room_id, room.id)
        self.assertFalse(interlocutors)
        self.assertEqual(last_message['id'], msg.id)

        await communicator.disconnect()

    async def test_get_support_room_if_in_room(self):
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.SUPPORT),
        ])

        room, support_room = rooms

        await support_room.participants.aset([self.admin_user])

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        async with join_room(communicator, room.id):
            response = await self.get_support_room(communicator)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            room_id = response['data']['id']
            interlocutors = response['data']['interlocutors']
            last_message = response['data']['last_message']

            self.assertEqual(room_id, support_room.id)
            self.assertFalse(interlocutors)
            self.assertIsNone(last_message)

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

        room_id = response['data']['id']
        interlocutors = response['data']['interlocutors']
        last_message = response['data']['last_message']

        self.assertFalse(interlocutors)
        self.assertIsNone(last_message)

        try:
            room = await Room.objects.prefetch_related('participants').aget(id=room_id)
        except Room.DoesNotExist:
            room = None

        self.assertIsNotNone(room)

        participants = room.participants.all()

        self.assertEqual(len(participants), 1)
        self.assertEqual(participants[0].id, self.admin_user.id)

        await communicator.disconnect()

    async def test_get_support_room_last_message_includes_attachments(self):
        room = await Room.objects.acreate(type=Room.SUPPORT)
        await room.participants.aset([self.admin_user])

        message = await Message.objects.acreate(
            text='test',
            user=self.admin_user,
            room=room
        )

        attachments = await MessageAttachment.objects.abulk_create([
            MessageAttachment(file='file1', message=message),
            MessageAttachment(file='file2', message=message),
        ])
        attachments_ids = [a.id for a in attachments]

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
