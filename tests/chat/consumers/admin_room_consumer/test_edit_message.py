import factory
from django.test import tag, TransactionTestCase, override_settings
from rest_framework import status

from core.apps.accounts.factories import UserAsyncFactory, UserFactory
from core.apps.chat.factories import MessageAsyncFactory, RoomAsyncFactory
from core.apps.chat.models import Room, Message
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
    }
)
@tag('slow', 'chats')
class AdminRoomConsumerEditMessageTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):

    def setUp(self):
        self.admin_user = UserFactory(admin=True)

    async def test_edit_message_not_in_room_not_allowed(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.admin_user])
        msg = await MessageAsyncFactory(user=self.admin_user, room=room)

        communicator = get_admin_communicator(self.admin_user)

        async with websocket_connect(communicator):
            response = await self.edit_message(communicator, msg.pk, 'edited')

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_edit_message(self):
        user = await UserAsyncFactory(has_sub=True)

        support_room, own_support_room = await RoomAsyncFactory(
            2, type=Room.SUPPORT, participants=factory.Iterator([[user], [self.admin_user]])
        )

        support_room_msg, own_support_room_msg = await MessageAsyncFactory(
            2, user=self.admin_user, room=factory.Iterator([support_room, own_support_room])
        )

        admin_communicator = get_admin_communicator(self.admin_user)
        user_communicator = get_user_communicator(user)

        async with websocket_connect_communal([admin_communicator, user_communicator]):
            # create another admin when current one is already connected
            # another_admin must be added to the list of groups to which the message is sent
            another_admin = await UserAsyncFactory(admin=True)
            another_admin_communicator = get_admin_communicator(another_admin)

            async with websocket_connect(another_admin_communicator):
                async with join_room_communal([admin_communicator, user_communicator], support_room.pk):
                    edited_text = 'edited'
                    admin_response = await self.edit_message(admin_communicator, support_room_msg.pk, edited_text)
                    user_response = await user_communicator.receive_json_from()
                    another_admin_response = await another_admin_communicator.receive_json_from()

                    # check that only one notification is sent
                    self.assertTrue(await admin_communicator.receive_nothing())
                    self.assertTrue(await user_communicator.receive_nothing())
                    self.assertTrue(await another_admin_communicator.receive_nothing())

                    # check that user and both admins were notified
                    for response in [admin_response, user_response, another_admin_response]:
                        self.assertEqual(response['response_status'], status.HTTP_200_OK)
                        self.assertEqual(response['data']['id'], support_room_msg.pk)
                        self.assertEqual(response['data']['text'], edited_text)

                    try:
                        msg = await Message.objects.aget(pk=support_room_msg.pk)
                    except (Message.DoesNotExist, Message.MultipleObjectsReturned):
                        msg = None

                    self.assertIsNotNone(msg)
                    self.assertEqual(msg.text, edited_text)  # check that text changed in the db

                async with join_room(admin_communicator, own_support_room.pk):
                    edited_text = 'edited'
                    admin_response = await self.edit_message(admin_communicator, own_support_room_msg.pk, edited_text)
                    another_admin_response = await another_admin_communicator.receive_json_from()

                    # check that only one notification is sent
                    self.assertTrue(await admin_communicator.receive_nothing())
                    self.assertTrue(await another_admin_communicator.receive_nothing())

                    # check that both admins were notified
                    for response in [admin_response, another_admin_response]:
                        self.assertEqual(response['response_status'], status.HTTP_200_OK)
                        self.assertEqual(response['data']['id'], own_support_room_msg.pk)
                        self.assertEqual(response['data']['text'], edited_text)

                    try:
                        msg = await Message.objects.aget(id=own_support_room_msg.pk)
                    except (Message.DoesNotExist, Message.MultipleObjectsReturned):
                        msg = None

                    self.assertIsNotNone(msg)
                    self.assertEqual(msg.text, edited_text)  # check that text changed in the db

    async def test_edit_message_of_another_user_not_allowed(self):
        user = await UserAsyncFactory()
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[user])
        message = await MessageAsyncFactory(user=user, room=room)

        communicator = get_admin_communicator(self.admin_user)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.edit_message(communicator, message.pk, 'edited')

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_edit_message_not_found(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.admin_user])

        communicator = get_admin_communicator(self.admin_user)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.edit_message(communicator, -1, 'edited')

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_edit_message_not_in_support_room_not_allowed(self):
        user = await UserAsyncFactory()

        match_room, instant_room = await RoomAsyncFactory(
            2,
            type=factory.Iterator([Room.MATCH, Room.INSTANT]),
            participants=[user]
        )

        match_room_msg, instant_room_msg = await MessageAsyncFactory(
            2, user=user, room=factory.Iterator([match_room, instant_room])
        )

        communicator = get_admin_communicator(self.admin_user)

        async with websocket_connect(communicator):
            async with join_room(communicator, match_room.pk):
                response = await self.edit_message(communicator, match_room_msg.pk, 'edited')

                self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
                self.assertIsNone(response['data'])
                self.assertTrue(response['errors'])

            async with join_room(communicator, instant_room.pk):
                response = await self.edit_message(communicator, instant_room_msg.pk, 'edited')

                self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
                self.assertIsNone(response['data'])
                self.assertTrue(response['errors'])
