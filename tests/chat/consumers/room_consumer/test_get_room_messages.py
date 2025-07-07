import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.chat.factories import RoomAsyncFactory, MessageAsyncFactory
from core.apps.payments.factories import SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import join_room_communal, join_room, get_user_communicator, websocket_connect


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
class RoomConsumerGetRoomMessagesTestCase(TransactionTestCase, RoomConsumerActionsMixin):

    def setUp(self):
        self.user1, self.user2 = UserFactory.create_batch(2, has_sub=True)

    async def test_get_room_messages_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        room = await RoomAsyncFactory(participants=[user_wo_active_sub])
        sub = await SubscriptionAsyncFactory(brand__user=user_wo_active_sub)  # create active sub

        communicator = get_user_communicator(user_wo_active_sub)

        async with join_room(communicator, room.pk, connect=True):
            # make sub inactive
            sub.is_active = False
            await sub.asave()

            response = await self.get_room_messages(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

    async def test_get_room_messages_not_in_room_not_allowed(self):
        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            response = await self.get_room_messages(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertTrue(response['errors'])
        self.assertIsNone(response['data'])

    async def test_get_room_messages(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])

        messages = await MessageAsyncFactory(
            3,
            user=factory.Iterator([self.user1, self.user2, self.user2]),
            room=room
        )

        communicator1 = get_user_communicator(self.user1)
        communicator2 = get_user_communicator(self.user2)

        async with join_room_communal([communicator1, communicator2], room.pk, connect=True):
            response = await self.get_room_messages(communicator1, 1)
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to the second user

        self.assertEqual(response['response_status'], status.HTTP_200_OK)
        self.assertEqual(len(response['data']['results']), len(messages))

    async def test_get_room_messages_returns_only_current_room_messages(self):
        room1, room2 = await RoomAsyncFactory(2, participants=[self.user1, self.user2])

        room1_messages = await MessageAsyncFactory(
            3,
            user=factory.Iterator([self.user1, self.user2, self.user2]),
            room=room1
        )

        await MessageAsyncFactory(2, user=factory.Iterator([self.user1, self.user2]), room=room2)

        communicator = get_user_communicator(self.user1)

        async with join_room(communicator, room1.pk, connect=True):
            response = await self.get_room_messages(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)
        self.assertEqual(len(response['data']['results']), len(room1_messages))

    async def test_get_room_messages_pagination(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])
        messages = await MessageAsyncFactory(120, user=factory.Iterator([self.user1, self.user2]), room=room)

        communicator = get_user_communicator(self.user1)

        async with join_room(communicator, room.pk, connect=True):
            # first page
            response = await self.get_room_messages(communicator, 1)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            self.assertEqual(response['data']['count'], len(messages))
            self.assertEqual(len(response['data']['results']), 100)
            self.assertEqual(response['data']['next'], 2)

            # second page
            response = await self.get_room_messages(communicator, 2)

            self.assertEqual(response['response_status'], status.HTTP_200_OK)
            self.assertEqual(len(response['data']['results']), 20)
            self.assertIsNone(response['data']['next'])

            # negative page number
            response = await self.get_room_messages(communicator, -1)

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertTrue(response['errors'])
            self.assertIsNone(response['data'])

            # page number is not a number
            response = await self.get_room_messages(communicator, 'asf')

            self.assertEqual(response['response_status'], status.HTTP_400_BAD_REQUEST)
            self.assertTrue(response['errors'])
            self.assertIsNone(response['data'])

    async def test_get_room_messages_include_attachments(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])
        message = await MessageAsyncFactory(user=self.user1, room=room, has_attachments=True)
        attachments_ids = [pk async for pk in message.attachments.values_list('pk', flat=True).aiterator()]

        communicator = get_user_communicator(self.user1)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.get_room_messages(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        results = response['data']['results']
        self.assertEqual(len(results), 1)
        self.assertTrue('attachments' in results[0])

        response_attachments_ids = [a['id'] for a in results[0]['attachments']]
        self.assertEqual(response_attachments_ids, attachments_ids)
