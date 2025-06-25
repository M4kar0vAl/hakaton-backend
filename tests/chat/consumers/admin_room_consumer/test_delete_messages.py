import factory
from django.test import tag, TransactionTestCase, override_settings
from rest_framework import status

from core.apps.accounts.factories import UserAsyncFactory, UserFactory
from core.apps.chat.factories import MessageAsyncFactory, RoomAsyncFactory
from core.apps.chat.models import Room, Message, MessageAttachment
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
class AdminRoomConsumerDeleteMessagesTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):

    def setUp(self):
        self.admin_user = UserFactory(admin=True)

    async def test_delete_messages_not_in_room_not_allowed(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.admin_user])
        msg = await MessageAsyncFactory(user=self.admin_user, room=room)

        communicator = get_admin_communicator(self.admin_user)

        async with websocket_connect(communicator):
            response = await self.delete_messages(communicator, [msg.pk])

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_delete_messages(self):
        user = await UserAsyncFactory()
        await SubscriptionAsyncFactory(brand__user=user)

        support_room, own_support_room = await RoomAsyncFactory(
            2, type=Room.SUPPORT, participants=factory.Iterator([[user], [self.admin_user]])
        )

        support_room_msg, *own_support_room_msgs = await MessageAsyncFactory(
            3,
            user=self.admin_user,
            room=factory.Iterator([support_room, own_support_room, own_support_room])
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
                    admin_response = await self.delete_messages(admin_communicator, [support_room_msg.pk])
                    user_response = await user_communicator.receive_json_from()
                    another_admin_response = await another_admin_communicator.receive_json_from()

                    # check that only one notification is sent
                    self.assertTrue(await admin_communicator.receive_nothing())
                    self.assertTrue(await user_communicator.receive_nothing())
                    self.assertTrue(await another_admin_communicator.receive_nothing())

                    # check that user and both admins were notified
                    for response in [admin_response, user_response, another_admin_response]:
                        self.assertEqual(response['response_status'], status.HTTP_200_OK)
                        self.assertEqual(response['data']['messages_ids'], [support_room_msg.pk])

                    # check that messages were deleted from db
                    self.assertFalse(await Message.objects.filter(id__in=[support_room_msg.pk]).aexists())

                async with join_room(admin_communicator, own_support_room.pk):
                    own_support_room_msgs_ids = [msg.pk for msg in own_support_room_msgs]
                    admin_response = await self.delete_messages(admin_communicator, own_support_room_msgs_ids)
                    another_admin_response = await another_admin_communicator.receive_json_from()

                    # check that only one notification is sent
                    self.assertTrue(await admin_communicator.receive_nothing())
                    self.assertTrue(await another_admin_communicator.receive_nothing())

                    # check that both admins were notified
                    for response in [admin_response, another_admin_response]:
                        self.assertEqual(response['response_status'], status.HTTP_200_OK)
                        self.assertEqual(response['data']['messages_ids'], own_support_room_msgs_ids)

                    # check that messages were deleted from db
                    self.assertFalse(await Message.objects.filter(id__in=own_support_room_msgs_ids).aexists())

    async def test_delete_messages_all_not_found(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.admin_user])

        communicator = get_admin_communicator(self.admin_user)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.delete_messages(communicator, [0, -1])

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_delete_messages_some_not_found(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[self.admin_user])
        msg = await MessageAsyncFactory(user=self.admin_user, room=room)

        communicator = get_admin_communicator(self.admin_user)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.delete_messages(communicator, [msg.pk, -1])

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        # check that existing message was not deleted
        self.assertTrue(await Message.objects.filter(id=msg.pk).aexists())

    async def test_delete_messages_of_another_user_not_allowed(self):
        user = await UserAsyncFactory()
        room = await RoomAsyncFactory(type=Room.SUPPORT, participants=[user])
        msg = await MessageAsyncFactory(user=user, room=room)

        communicator = get_admin_communicator(self.admin_user)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.delete_messages(communicator, [msg.pk])

        self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        self.assertTrue(await Message.objects.filter(id=msg.pk).aexists())

    async def test_delete_messages_not_in_support_room_not_allowed(self):
        user = await UserAsyncFactory()
        match_room, instant_room = await RoomAsyncFactory(2, type=factory.Iterator([Room.MATCH, Room.INSTANT]))

        match_room_msg, instant_room_msg = await MessageAsyncFactory(
            2, user=user, room=factory.Iterator([match_room, instant_room])
        )

        communicator = get_admin_communicator(self.admin_user)

        async with websocket_connect(communicator):
            async with join_room(communicator, match_room.pk):
                response = await self.delete_messages(communicator, [match_room_msg.pk])

                self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
                self.assertIsNone(response['data'])
                self.assertTrue(response['errors'])

            async with join_room(communicator, instant_room.pk):
                response = await self.delete_messages(communicator, [instant_room_msg.pk])

                self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
                self.assertIsNone(response['data'])
                self.assertTrue(response['errors'])

    async def test_delete_messages_with_attachments(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT)
        message = await MessageAsyncFactory(user=self.admin_user, room=room, has_attachments=True)
        attachments_ids = [pk async for pk in message.attachments.values_list('pk', flat=True).aiterator()]

        communicator = get_admin_communicator(self.admin_user)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.delete_messages(communicator, [message.pk])

        self.assertEqual(response['response_status'], status.HTTP_200_OK)

        # check that attachments were deleted
        self.assertFalse(
            await MessageAttachment.objects.filter(id__in=attachments_ids).aexists()
        )
