import factory
from django.test import tag, TransactionTestCase, override_settings
from rest_framework import status

from core.apps.accounts.factories import UserAsyncFactory, UserFactory
from core.apps.chat.consumers import AdminRoomConsumer, RoomConsumer
from core.apps.chat.factories import RoomAsyncFactory, MessageAttachmentAsyncFactory
from core.apps.chat.models import Room, Message, MessageAttachment
from core.apps.payments.factories import SubscriptionAsyncFactory
from tests.mixins import AdminRoomConsumerActionsMixin
from tests.utils import join_room, get_websocket_communicator_for_user, join_room_communal


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
class AdminRoomConsumerCreateMessageTestCase(TransactionTestCase, AdminRoomConsumerActionsMixin):

    def setUp(self):
        self.admin_user = UserFactory(admin=True)

        self.path = 'ws/admin-chat/'
        self.accepted_protocol = 'admin-chat'

        self.user_path = 'ws/chat/'
        self.user_accepted_protocol = 'chat'

    async def test_create_message_not_in_room_not_allowed(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.create_message(communicator, 'test')

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message_not_in_support_room_not_allowed(self):
        match_room, instant_room = await RoomAsyncFactory(2, type=factory.Iterator([Room.MATCH, Room.INSTANT]))

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.admin_user
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, match_room.pk):
            response = await self.create_message(communicator, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        async with join_room(communicator, instant_room.pk):
            response = await self.create_message(communicator, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message(self):
        user = await UserAsyncFactory()
        await SubscriptionAsyncFactory(brand__user=user)

        support_room, own_support_room = await RoomAsyncFactory(
            2, type=Room.SUPPORT, participants=factory.Iterator([[user], [self.admin_user]])
        )

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
            user=user
        )

        admin_connected, _ = await admin_communicator.connect()
        user_connected, _ = await user_communicator.connect()

        self.assertTrue(admin_connected)
        self.assertTrue(user_connected)

        # create another admin when current one is already connected
        # another_admin must be added to the list of groups to which the message is sent
        another_admin = await UserAsyncFactory(admin=True)

        another_admin_communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.accepted_protocol],
            user=another_admin
        )

        another_admin_connected, _ = await another_admin_communicator.connect()
        self.assertTrue(another_admin_connected)

        async with join_room_communal([admin_communicator, user_communicator], support_room.pk):
            msg_text = 'test'
            admin_response = await self.create_message(admin_communicator, msg_text)
            user_response = await user_communicator.receive_json_from()  # check that user receives message
            another_admin_response = await another_admin_communicator.receive_json_from()

            # check that only one notification is sent
            self.assertTrue(await admin_communicator.receive_nothing())
            self.assertTrue(await user_communicator.receive_nothing())
            self.assertTrue(await another_admin_communicator.receive_nothing())

            # check that user and both admins got the message
            for response in [admin_response, user_response, another_admin_response]:
                self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
                self.assertEqual(response['data']['text'], msg_text)

            msg_id = admin_response['data']['id']
            try:
                msg = await Message.objects.filter(room=support_room).aget()
            except (Message.DoesNotExist, Message.MultipleObjectReturned):
                msg = None

            self.assertIsNotNone(msg)
            self.assertEqual(msg.pk, msg_id)

        await user_communicator.disconnect()

        async with join_room(admin_communicator, own_support_room.pk):
            msg_text = 'test'
            admin_response = await self.create_message(admin_communicator, msg_text)
            another_admin_response = await another_admin_communicator.receive_json_from()

            # check that only one notification is sent
            self.assertTrue(await admin_communicator.receive_nothing())
            self.assertTrue(await another_admin_communicator.receive_nothing())

            # check that both admins got the message
            for response in [admin_response, another_admin_response]:
                self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
                self.assertEqual(response['data']['text'], msg_text)

            msg_id = admin_response['data']['id']
            try:
                msg = await Message.objects.filter(room=own_support_room).aget()
            except (Message.DoesNotExist, Message.MultipleObjectReturned):
                msg = None

            self.assertIsNotNone(msg)
            self.assertEqual(msg.pk, msg_id)

        await admin_communicator.disconnect()
        await another_admin_communicator.disconnect()

    async def test_create_message_with_attachments(self):
        room = await RoomAsyncFactory(type=Room.SUPPORT)
        attachments = await MessageAttachmentAsyncFactory(2)
        attachments_ids = [a.pk for a in attachments]

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
            response = await self.create_message(communicator, 'any text', attachments_ids)
            response_attachments_ids = [a['id'] for a in response['data']['attachments']]

            self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
            self.assertEqual(attachments_ids, response_attachments_ids)

            msg_id = response['data']['id']

            # check that attachments were connected to the message
            self.assertEqual(
                await MessageAttachment.objects.filter(id__in=attachments_ids, message_id=msg_id).acount(),
                2
            )

        await communicator.disconnect()
