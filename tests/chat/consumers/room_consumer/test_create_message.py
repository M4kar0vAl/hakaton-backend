import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory, AdminUserAsyncFactory
from core.apps.blacklist.factories import BlackListAsyncFactory
from core.apps.brand.factories import (
    BrandShortFactory,
    InstantCoopAsyncFactory
)
from core.apps.chat.consumers import RoomConsumer, AdminRoomConsumer
from core.apps.chat.factories import (
    RoomAsyncFactory,
    RoomInstantAsyncFactory,
    MessageAsyncFactory,
    MessageAttachmentAsyncFactory, RoomMatchAsyncFactory
)
from core.apps.chat.models import Room, MessageAttachment
from core.apps.payments.factories import SubscriptionFactory, SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import get_websocket_communicator_for_user, join_room_communal, join_room


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class RoomConsumerCreateMessageTestCase(TransactionTestCase, RoomConsumerActionsMixin):
    serialized_rollback = True

    def setUp(self):
        self.user1, self.user2 = UserFactory.create_batch(2)
        self.brand1, self.brand2 = BrandShortFactory.create_batch(2, user=factory.Iterator([self.user1, self.user2]))

        SubscriptionFactory.create_batch(2, brand=factory.Iterator([self.brand1, self.brand2]))

        self.path = 'ws/chat/'
        self.accepted_protocol = 'chat'

        self.admin_path = 'ws/admin-chat/'
        self.admin_accepted_protocol = 'admin-chat'

    async def test_create_message_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        room = await RoomAsyncFactory(participants=[user_wo_active_sub])

        # create active sub
        # users can connect to consumer only with active sub
        sub = await SubscriptionAsyncFactory(brand__user=user_wo_active_sub)

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=user_wo_active_sub
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            # deactivate sub for create_message action test
            sub.is_active = False
            await sub.asave()

            response = await self.create_message(communicator, 'test')
            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

        await communicator.disconnect()

    async def test_create_message_not_in_room_not_allowed(self):
        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.create_message(communicator, 'asf')
        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_create_message_if_brand_in_blacklist_of_interlocutor_not_allowed(self):
        room = await RoomMatchAsyncFactory(participants=[self.user1, self.user2])
        await BlackListAsyncFactory(initiator=self.brand2, blocked=self.brand1)  # brand2 blocks brand1

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            response = await self.create_message(communicator, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message_if_interlocutor_in_blacklist_of_brand_not_allowed(self):
        room = await RoomMatchAsyncFactory(participants=[self.user1, self.user2])
        await BlackListAsyncFactory(initiator=self.brand1, blocked=self.brand2)  # brand1 blocks brand2

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            response = await self.create_message(communicator, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message(self):
        both_users = [self.user1, self.user2]
        match_room, instant_room, support_room = await RoomAsyncFactory(
            3,
            type=factory.Iterator([Room.MATCH, Room.INSTANT, Room.SUPPORT]),
            participants=factory.Iterator([both_users, both_users, [self.user1]])
        )

        await InstantCoopAsyncFactory(initiator=self.brand1, target=self.brand2, room=instant_room)

        # initial admin (that was before the user connected to websocket)
        admin1 = await AdminUserAsyncFactory()

        communicator1 = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        communicator2 = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user2
        )

        admin_communicator1 = get_websocket_communicator_for_user(
            url_pattern=self.admin_path,
            path=self.admin_path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.admin_accepted_protocol],
            user=admin1
        )

        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        connected3, _ = await admin_communicator1.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)
        self.assertTrue(connected3)

        # create another admin when user is already connected
        # admin2 must be added to the list of groups to which the message is sent
        admin2 = await AdminUserAsyncFactory()

        admin_communicator2 = get_websocket_communicator_for_user(
            url_pattern=self.admin_path,
            path=self.admin_path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.admin_accepted_protocol],
            user=admin2
        )

        connected4, _ = await admin_communicator2.connect()
        self.assertTrue(connected4)

        async with join_room_communal([communicator1, communicator2], match_room.pk):
            msg_text = 'test'
            response1 = await self.create_message(communicator1, msg_text)
            response2 = await communicator2.receive_json_from()

            # check that admins aren't notified about non-support room actions
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response1, response2]:
                self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
                self.assertEqual(response['data']['text'], msg_text)
                self.assertEqual(response['data']['room'], match_room.pk)

        async with join_room_communal([communicator1, communicator2], instant_room.pk):
            msg_text = 'test'
            response1 = await self.create_message(communicator1, msg_text)
            response2 = await communicator2.receive_json_from()

            # check that admins aren't notified about non-support room actions
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response1, response2]:
                self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
                self.assertEqual(response['data']['text'], msg_text)
                self.assertEqual(response['data']['room'], instant_room.pk)

        async with join_room(communicator1, support_room.pk):
            msg_text = 'test'
            response1 = await self.create_message(communicator1, msg_text)
            admin1_response = await admin_communicator1.receive_json_from()
            admin2_response = await admin_communicator2.receive_json_from()

            # check that only one notification is sent
            self.assertTrue(await communicator1.receive_nothing())
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            # check that both admins were notified
            for response in [response1, admin1_response, admin2_response]:
                self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
                self.assertEqual(response['data']['text'], msg_text)
                self.assertEqual(response['data']['room'], support_room.pk)

        await communicator1.disconnect()
        await communicator2.disconnect()
        await admin_communicator1.disconnect()
        await admin_communicator2.disconnect()

    async def test_create_message_instant_room_not_allowed_if_message_by_user_already_created(self):
        room = await RoomInstantAsyncFactory(participants=[self.user1, self.user2])
        await InstantCoopAsyncFactory(initiator=self.brand1, target=self.brand2, room=room)
        await MessageAsyncFactory(user=self.user1, room=room)

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            response = await self.create_message(communicator, 'asf')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message_in_instant_room_user_is_not_the_initiator_of_coop(self):
        room = await RoomInstantAsyncFactory(participants=[self.user1, self.user2])
        await InstantCoopAsyncFactory(initiator=self.brand1, target=self.brand2, room=room)

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user2
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            response = await self.create_message(communicator, 'asf')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_create_message_with_attachments(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])
        attachments = await MessageAttachmentAsyncFactory(2, file='')
        attachments_ids = [a.pk for a in attachments]

        communicator1 = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        communicator2 = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user2
        )

        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        async with join_room_communal([communicator1, communicator2], room.pk):
            response1 = await self.create_message(communicator1, 'any text', attachments_ids)
            response2 = await communicator2.receive_json_from()

            for response in [response1, response2]:
                response_attachments_ids = [a['id'] for a in response['data']['attachments']]

                self.assertEqual(response['response_status'], status.HTTP_201_CREATED)
                self.assertEqual(attachments_ids, response_attachments_ids)

            msg_id = response1['data']['id']

            # check that attachments were connected to the message
            self.assertEqual(
                await MessageAttachment.objects.filter(id__in=attachments_ids, message_id=msg_id).acount(),
                2
            )

        await communicator1.disconnect()
        await communicator2.disconnect()
