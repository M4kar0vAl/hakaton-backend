import factory
from django.test import tag, TransactionTestCase, override_settings
from rest_framework import status

from core.apps.accounts.factories import UserAsyncFactory, UserFactory
from core.apps.chat.consumers import AdminRoomConsumer, RoomConsumer
from core.apps.chat.factories import RoomAsyncFactory, RoomSupportAsyncFactory, MessageAsyncFactory
from core.apps.chat.models import Room
from core.apps.payments.factories import SubscriptionAsyncFactory
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import join_room, get_websocket_communicator_for_user, join_room_communal


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerGetRoomMessagesTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):
    serialized_rollback = True

    def setUp(self):
        self.admin_user = UserFactory(admin=True)

        self.path = 'ws/admin-chat/'
        self.accepted_protocol = 'admin-chat'

        self.user_path = 'ws/chat/'
        self.user_accepted_protocol = 'chat'

    async def test_get_room_messages_not_in_room_not_allowed(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.get_room_messages(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_get_room_messages(self):
        user1, user2 = await UserAsyncFactory(2)
        await SubscriptionAsyncFactory(brand__user=user1)

        match_room, instant_room = await RoomAsyncFactory(
            2,
            type=factory.Iterator([Room.MATCH, Room.INSTANT]),
            participants=[user1, user2]
        )
        support_room, own_support_room = await RoomSupportAsyncFactory(
            2, participants=factory.Iterator([[user1], [self.admin_user]])
        )

        await MessageAsyncFactory(3, user=user1, room=factory.Iterator([match_room, instant_room, support_room]))
        await MessageAsyncFactory(1, user=self.admin_user, room=own_support_room)

        messages = await MessageAsyncFactory(2, user=user2, room=factory.Iterator([match_room, instant_room]))
        messages.extend(
            await MessageAsyncFactory(2, user=self.admin_user, room=factory.Iterator([support_room, own_support_room])))

        admin_communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        user_communicator = get_websocket_communicator_for_user(
            url_pattern=self.user_path,
            path=self.user_path,
            consumer_class=RoomConsumer,
            protocols=[self.user_accepted_protocol],
            user=user1
        )

        admin_connected, _ = await admin_communicator.connect()
        user_connected, _ = await user_communicator.connect()

        self.assertTrue(admin_connected)
        self.assertTrue(user_connected)

        async with join_room_communal([admin_communicator, user_communicator], match_room.pk) as responses:
            for response in responses:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            response = await self.get_room_messages(admin_communicator, 1)
            self.assertTrue(await user_communicator.receive_nothing())

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            messages_resp = response['data']['results']

            self.assertEqual(len(messages_resp), 2)
            # check that messages ordered by created_at desc
            self.assertEqual(messages_resp[0]['id'], messages[0].pk)

        async with join_room_communal([admin_communicator, user_communicator], instant_room.pk) as responses:
            for response in responses:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            response = await self.get_room_messages(admin_communicator, 1)
            self.assertTrue(await user_communicator.receive_nothing())

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            messages_resp = response['data']['results']

            self.assertEqual(len(messages_resp), 2)
            # check that messages ordered by created_at desc
            self.assertEqual(messages_resp[0]['id'], messages[1].pk)

        async with join_room_communal([admin_communicator, user_communicator], support_room.pk) as responses:
            for response in responses:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            response = await self.get_room_messages(admin_communicator, 1)
            self.assertTrue(await user_communicator.receive_nothing())

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            messages_resp = response['data']['results']

            self.assertEqual(len(messages_resp), 2)
            # check that messages ordered by created_at desc
            self.assertEqual(messages_resp[0]['id'], messages[2].pk)

        async with join_room(admin_communicator, own_support_room.pk) as response:
            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            response = await self.get_room_messages(admin_communicator, 1)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            messages_resp = response['data']['results']

            self.assertEqual(len(messages_resp), 2)
            # check that messages ordered by created_at desc
            self.assertEqual(messages_resp[0]['id'], messages[3].pk)

        await admin_communicator.disconnect()
        await user_communicator.disconnect()

    async def test_get_room_messages_pagination(self):
        user = await UserAsyncFactory()
        room = await RoomSupportAsyncFactory(participants=[user])
        messages = await MessageAsyncFactory(110, user=factory.Iterator([user, self.admin_user]), room=room)

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
            # first page
            response = await self.get_room_messages(communicator, 1)
            data = response['data']

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            self.assertEqual(data['count'], len(messages))
            self.assertEqual(len(data['results']), 100)
            self.assertEqual(data['next'], 2)

            # second page
            response = await self.get_room_messages(communicator, 2)
            data = response['data']

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            self.assertEqual(len(data['results']), 10)
            self.assertIsNone(data['next'])

            # negative page number
            response = await self.get_room_messages(communicator, -1)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

            # page number is not a number
            response = await self.get_room_messages(communicator, 'asf')

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_get_room_messages_include_attachments(self):
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

        async with join_room(communicator, room.pk):
            response = await self.get_room_messages(communicator, 1)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            results = response['data']['results']
            self.assertEqual(len(results), 1)
            self.assertTrue('attachments' in results[0])

            response_attachments_ids = [a['id'] for a in results[0]['attachments']]
            self.assertEqual(response_attachments_ids, attachments_ids)

        await communicator.disconnect()
