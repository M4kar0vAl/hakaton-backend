import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.brand.factories import BrandShortFactory
from core.apps.chat.consumers import RoomConsumer
from core.apps.chat.factories import (
    RoomAsyncFactory,
    MessageAsyncFactory
)
from core.apps.chat.models import Room
from core.apps.payments.factories import SubscriptionFactory, SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import get_websocket_communicator_for_user, join_room


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class RoomConsumerGetSupportRoomTestCase(TransactionTestCase, RoomConsumerActionsMixin):

    def setUp(self):
        self.user1, self.user2 = UserFactory.create_batch(2)
        self.brand1, self.brand2 = BrandShortFactory.create_batch(2, user=factory.Iterator([self.user1, self.user2]))

        SubscriptionFactory.create_batch(2, brand=factory.Iterator([self.brand1, self.brand2]))

        self.path = 'ws/chat/'
        self.accepted_protocol = 'chat'

    async def test_get_support_room_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        await RoomAsyncFactory(participants=[user_wo_active_sub])
        sub = await SubscriptionAsyncFactory(brand__user=user_wo_active_sub)  # create active sub

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=user_wo_active_sub
        )

        # connect with active sub
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # make sub inactive
        sub.is_active = False
        await sub.asave()

        response = await self.get_support_room(communicator)
        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

    async def test_get_support_room(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.user1])
        msg = await MessageAsyncFactory(user=self.user1, room=room)

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.get_support_room(communicator)
        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        data = response['data']

        self.assertEqual(data['id'], room.pk)
        self.assertFalse(data['interlocutors'])
        self.assertEqual(data['last_message']['id'], msg.pk)

    async def test_get_support_room_if_does_not_exist(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.get_support_room(communicator)
        await communicator.disconnect()

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

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room1.pk):
            response = await self.get_support_room(communicator)
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            room_id = response['data']['id']
            interlocutors = response['data']['interlocutors']

            self.assertEqual(room_id, support_room.pk)
            self.assertFalse(interlocutors)

        await communicator.disconnect()

    async def test_get_support_room_last_message_includes_attachments(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.user1])
        message = await MessageAsyncFactory(user=self.user1, room=room, has_attachments=True, attachments__file='')
        attachments_ids = [pk async for pk in message.attachments.values_list('pk', flat=True).aiterator()]

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.get_support_room(communicator)
        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        last_message = response['data']['last_message']
        self.assertTrue('attachments' in last_message)

        response_attachments_ids = [a['id'] for a in last_message['attachments']]
        self.assertEqual(response_attachments_ids, attachments_ids)
