import factory
from django.test import tag, TransactionTestCase, override_settings
from rest_framework import status

from core.apps.accounts.factories import UserFactory
from core.apps.chat.factories import RoomFactory
from core.apps.chat.models import Room
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import join_room, get_admin_communicator, websocket_connect


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerJoinRoomTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):

    def setUp(self):
        self.admin_user = UserFactory(admin=True)
        self.user1, self.user2 = UserFactory.create_batch(2)

        self.match_room, self.instant_room = RoomFactory.create_batch(
            2, type=factory.Iterator([Room.MATCH, Room.INSTANT]), participants=[self.user1, self.user2]
        )

        self.support_room, self.own_support_room = RoomFactory.create_batch(
            2, type=Room.SUPPORT, participants=factory.Iterator([[self.user1], [self.admin_user]])
        )

    async def test_join_room(self):
        communicator = get_admin_communicator(self.admin_user)

        async with websocket_connect(communicator):
            # join match room
            async with join_room(communicator, self.match_room.pk) as response:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            # join instant room
            async with join_room(communicator, self.instant_room.pk) as response:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            # join support room
            async with join_room(communicator, self.support_room.pk) as response:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

            # join own support room
            async with join_room(communicator, self.own_support_room.pk) as response:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)

    async def test_cannot_join_the_same_room(self):
        communicator = get_admin_communicator(self.admin_user)

        async with websocket_connect(communicator):
            # ----------MATCH room----------
            async with join_room(communicator, self.match_room.pk):
                response = await self.join_room(communicator, self.match_room.pk)

                self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
                self.assertIsNone(response['data'])
                self.assertTrue(response['errors'])

            # ----------INSTANT room----------
            async with join_room(communicator, self.instant_room.pk):
                response = await self.join_room(communicator, self.instant_room.pk)

                self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
                self.assertIsNone(response['data'])
                self.assertTrue(response['errors'])

            # ----------SUPPORT room----------
            async with join_room(communicator, self.support_room.pk):
                response = await self.join_room(communicator, self.support_room.pk)

                self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
                self.assertIsNone(response['data'])
                self.assertTrue(response['errors'])

            # ----------OWN SUPPORT room----------
            async with join_room(communicator, self.own_support_room.pk):
                response = await self.join_room(communicator, self.own_support_room.pk)

                self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
                self.assertIsNone(response['data'])
                self.assertTrue(response['errors'])

    async def test_cannot_join_another_room_before_leaving_the_previous_one(self):
        communicator = get_admin_communicator(self.admin_user)

        async with join_room(communicator, self.support_room.pk, connect=True):
            # try to join MATCH room
            response = await self.join_room(communicator, self.match_room.pk)
            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

            # try to join INSTANT room
            response = await self.join_room(communicator, self.instant_room.pk)
            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

            # try to join OWN SUPPORT room
            response = await self.join_room(communicator, self.own_support_room.pk)
            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
