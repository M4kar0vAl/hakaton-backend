import factory
from django.test import tag, TransactionTestCase, override_settings
from rest_framework import status

from core.apps.accounts.factories import UserAsyncFactory, UserFactory
from core.apps.chat.factories import RoomAsyncFactory, MessageAsyncFactory
from core.apps.chat.models import Room
from core.apps.payments.factories import SubscriptionAsyncFactory
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import (
    join_room,
    join_room_communal,
    get_admin_communicator,
    get_user_communicator,
    websocket_connect,
    websocket_connect_communal
)


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
class AdminRoomConsumerGetRoomMessagesTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):

    def setUp(self):
        self.admin_user = UserFactory(admin=True)

    async def test_get_room_messages_not_in_room_not_allowed(self):
        communicator = get_admin_communicator(self.admin_user)

        async with websocket_connect(communicator):
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
        support_room, own_support_room = await RoomAsyncFactory(
            2, type=Room.SUPPORT, participants=factory.Iterator([[user1], [self.admin_user]])
        )

        await MessageAsyncFactory(3, user=user1, room=factory.Iterator([match_room, instant_room, support_room]))
        await MessageAsyncFactory(1, user=self.admin_user, room=own_support_room)

        messages = await MessageAsyncFactory(2, user=user2, room=factory.Iterator([match_room, instant_room]))
        messages.extend(
            await MessageAsyncFactory(2, user=self.admin_user, room=factory.Iterator([support_room, own_support_room])))

        admin_communicator = get_admin_communicator(self.admin_user)
        user_communicator = get_user_communicator(user1)

        async with websocket_connect_communal([admin_communicator, user_communicator]):
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

    async def test_get_room_messages_pagination(self):
        user = await UserAsyncFactory()
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[user])
        messages = await MessageAsyncFactory(110, user=factory.Iterator([user, self.admin_user]), room=room)

        communicator = get_admin_communicator(self.admin_user)

        async with join_room(communicator, room.pk, connect=True):
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

    async def test_get_room_messages_include_attachments(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT)
        message = await MessageAsyncFactory(user=self.admin_user, room=room, has_attachments=True)
        attachments_ids = [pk async for pk in message.attachments.values_list('pk', flat=True).aiterator()]

        communicator = get_admin_communicator(self.admin_user)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.get_room_messages(communicator, 1)

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        results = response['data']['results']
        self.assertEqual(len(results), 1)
        self.assertTrue('attachments' in results[0])

        response_attachments_ids = [a['id'] for a in results[0]['attachments']]
        self.assertEqual(response_attachments_ids, attachments_ids)
