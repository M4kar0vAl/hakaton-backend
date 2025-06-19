import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserAsyncFactory, UserFactory
from core.apps.chat.consumers import AdminRoomConsumer
from core.apps.chat.factories import RoomAsyncFactory, RoomSupportAsyncFactory, MessageAsyncFactory
from core.apps.chat.models import Room
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import get_websocket_communicator_for_user


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerGetRoomsTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):
    serialized_rollback = True

    def setUp(self):
        self.admin_user = UserFactory(admin=True)

        self.path = 'ws/admin-chat/'
        self.accepted_protocol = 'admin-chat'

    async def test_get_rooms(self):
        user1, user2 = await UserAsyncFactory(2)
        another_admin = await UserAsyncFactory(admin=True)

        (
            support_room1,
            support_room2,
            own_support_room,
            support_another_admin
        ) = support_rooms = await RoomSupportAsyncFactory(
            4, participants=factory.Iterator([[user1], [user2], [self.admin_user], [another_admin]])
        )

        (
            match_room,
            instant_room,
            match_room_1_deleted,
            instant_room_1_deleted
        ) = other_rooms = await RoomAsyncFactory(
            4,
            type=factory.Iterator([Room.MATCH, Room.INSTANT]),
            participants=factory.Iterator([[user1, user2], [user1, user2], [user1], [user1]])
        )
        rooms = support_rooms + other_rooms

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.get_rooms(communicator, 1)
        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_200_OK)
        results = response['data']['results']

        self.assertEqual(len(results), len(rooms))  # admins get all rooms

        support_room1_response = list(filter(lambda obj: obj['id'] == support_room1.pk, results))
        support_room2_response = list(filter(lambda obj: obj['id'] == support_room2.pk, results))
        own_support_room_response = list(filter(lambda obj: obj['id'] == own_support_room.pk, results))
        support_another_admin_response = list(
            filter(lambda obj: obj['id'] == support_another_admin.pk, results)
        )
        match_room_response = list(filter(lambda obj: obj['id'] == match_room.pk, results))
        match_room_1_deleted_response = list(filter(lambda obj: obj['id'] == match_room_1_deleted.pk, results))
        instant_room_response = list(filter(lambda obj: obj['id'] == instant_room.pk, results))
        instant_room_1_deleted_response = list(
            filter(lambda obj: obj['id'] == instant_room_1_deleted.pk, results)
        )

        # check number of interlocutors in rooms
        # check support rooms of users
        self.assertEqual(len(support_room1_response[0]['interlocutors']), 1)
        self.assertEqual(len(support_room2_response[0]['interlocutors']), 1)

        # check own support room
        self.assertEqual(len(own_support_room_response[0]['interlocutors']), 0)  # change to W2W agency

        # check support room of another admin
        self.assertEqual(len(support_another_admin_response[0]['interlocutors']), 1)
        self.assertEqual(support_another_admin_response[0]['interlocutors'][0]['id'], another_admin.pk)

        # check match room
        self.assertEqual(len(match_room_response[0]['interlocutors']), 2)

        # check match room with 1 deleted user
        self.assertEqual(len(match_room_1_deleted_response[0]['interlocutors']), 1)

        # check instant room
        self.assertEqual(len(instant_room_response[0]['interlocutors']), 2)

        # check instant room with 1 deleted user
        self.assertEqual(len(instant_room_1_deleted_response[0]['interlocutors']), 1)

    async def test_get_rooms_pagination(self):
        rooms = await RoomSupportAsyncFactory(120)
        message1 = await MessageAsyncFactory(user=self.admin_user, room=rooms[10])
        message2 = await MessageAsyncFactory(user=self.admin_user, room=rooms[11])

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # page 1
        response = await self.get_rooms(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)
        data = response['data']
        results = data['results']

        self.assertEqual(data['count'], len(rooms))
        self.assertEqual(len(results), 100)
        self.assertEqual(data['next'], 2)

        # check ordering
        # rooms are ordered by the room last message's 'created_at' field descending
        self.assertEqual(results[0]['last_message']['id'], message2.pk)
        self.assertEqual(results[1]['last_message']['id'], message1.pk)

        # page 2
        response = await self.get_rooms(communicator, 2)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)
        data = response['data']

        self.assertEqual(len(data['results']), 20)
        self.assertIsNone(data['next'])

        await communicator.disconnect()

    async def test_get_rooms_last_message_includes_attachments(self):
        room = await RoomSupportAsyncFactory()
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

        response = await self.get_rooms(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        results = response['data']['results']
        self.assertEqual(len(results), 1)

        last_message = results[0]['last_message']
        self.assertTrue('attachments' in last_message)

        response_attachments_ids = [a['id'] for a in last_message['attachments']]
        self.assertEqual(response_attachments_ids, attachments_ids)

        await communicator.disconnect()
