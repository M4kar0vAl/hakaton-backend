import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.blacklist.factories import BlackListAsyncFactory
from core.apps.brand.factories import (
    BrandShortFactory,
    MatchAsyncFactory
)
from core.apps.chat.consumers import RoomConsumer, AdminRoomConsumer
from core.apps.chat.factories import RoomAsyncFactory, MessageAsyncFactory
from core.apps.chat.models import Room, Message, MessageAttachment
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
class RoomConsumerDeleteMessagesTestCase(TransactionTestCase, RoomConsumerActionsMixin):

    def setUp(self):
        self.user1, self.user2 = UserFactory.create_batch(2)
        self.brand1, self.brand2 = BrandShortFactory.create_batch(2, user=factory.Iterator([self.user1, self.user2]))

        SubscriptionFactory.create_batch(2, brand=factory.Iterator([self.brand1, self.brand2]))

        self.path = 'ws/chat/'
        self.accepted_protocol = 'chat'

        self.admin_path = 'ws/admin-chat/'
        self.admin_accepted_protocol = 'admin-chat'

    async def test_delete_messages_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        room = await RoomAsyncFactory(participants=[user_wo_active_sub])
        msg = await MessageAsyncFactory(user=user_wo_active_sub, room=room)
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

        async with join_room(communicator, room.pk):
            # make sub inactive
            sub.is_active = False
            await sub.asave()

            response = await self.delete_messages(communicator, [msg.pk])
            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

        await communicator.disconnect()

    async def test_delete_messages_not_in_room_not_allowed(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])
        message = await MessageAsyncFactory(user=self.user1, room=room)

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.delete_messages(communicator, [message.pk])
        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])
        self.assertTrue(await Message.objects.filter(id=message.pk).aexists())

    async def test_delete_messages_if_brand_in_blacklist_of_interlocutor_not_allowed(self):
        room = await RoomAsyncFactory(type=Room.MATCH, participants=[self.user1, self.user2])
        msg = await MessageAsyncFactory(user=self.user1, room=room)
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
            response = await self.delete_messages(communicator, [msg.pk])

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_delete_messages_if_interlocutor_in_blacklist_of_brand_not_allowed(self):
        room = await RoomAsyncFactory(type=Room.MATCH, participants=[self.user1, self.user2])
        msg = await MessageAsyncFactory(user=self.user1, room=room)
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
            response = await self.delete_messages(communicator, [msg.pk])

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_delete_messages_all_not_found(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])

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
            response = await self.delete_messages(communicator1, [0, -1])
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to the second user

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_delete_messages(self):
        both_users = [self.user1, self.user2]
        rooms = await RoomAsyncFactory(
            3,
            type=factory.Iterator([Room.MATCH, Room.INSTANT, Room.SUPPORT]),
            participants=factory.Iterator([both_users, both_users, [self.user1]])
        )
        match_room, instant_room, support_room = rooms

        await MatchAsyncFactory(instant_coop=True, initiator=self.brand1, target=self.brand2, room=instant_room)

        messages = await MessageAsyncFactory(6, user=self.user1, room=factory.Iterator(rooms))
        match_room_messages_ids = [msg.pk for msg in messages if msg.room_id == match_room.pk]
        instant_room_messages_ids = [msg.pk for msg in messages if msg.room_id == instant_room.pk]
        support_room_messages_ids = [msg.pk for msg in messages if msg.room_id == support_room.pk]

        # initial admin (that was before the user connected to websocket)
        admin1 = await UserAsyncFactory(admin=True)

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
        admin2 = await UserAsyncFactory(admin=True)

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
            response1 = await self.delete_messages(communicator1, match_room_messages_ids)
            response2 = await communicator2.receive_json_from()

            # check that admins aren't notified about non-support room actions
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response1, response2]:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)
                self.assertEqual(response['data']['messages_ids'], match_room_messages_ids)
                self.assertEqual(response['data']['room_id'], match_room.pk)

            messages_exists = await Message.objects.filter(id__in=match_room_messages_ids).aexists()
            self.assertFalse(messages_exists)

        async with join_room_communal([communicator1, communicator2], instant_room.pk):
            response1 = await self.delete_messages(communicator1, instant_room_messages_ids)
            response2 = await communicator2.receive_json_from()

            # check that admins aren't notified about non-support room actions
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response1, response2]:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)
                self.assertEqual(response['data']['messages_ids'], instant_room_messages_ids)
                self.assertEqual(response['data']['room_id'], instant_room.pk)

        async with join_room(communicator1, support_room.pk):
            response = await self.delete_messages(communicator1, support_room_messages_ids)
            admin1_response = await admin_communicator1.receive_json_from()
            admin2_response = await admin_communicator2.receive_json_from()

            # check that only one notification is sent
            self.assertTrue(await communicator1.receive_nothing())
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response, admin1_response, admin2_response]:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)
                self.assertEqual(response['data']['messages_ids'], support_room_messages_ids)
                self.assertEqual(response['data']['room_id'], support_room.pk)

        await communicator1.disconnect()
        await communicator2.disconnect()
        await admin_communicator1.disconnect()
        await admin_communicator2.disconnect()

    async def test_delete_messages_of_another_user_not_allowed(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])
        messages = await MessageAsyncFactory(2, user=self.user2, room=room)
        messages_ids = [msg.pk for msg in messages]

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
            response = await self.delete_messages(communicator1, messages_ids)
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to the second user

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

            messages_exist = await Message.objects.filter(id__in=messages_ids).aexists()
            self.assertTrue(messages_exist)

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_delete_messages_some_not_found(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])
        messages = await MessageAsyncFactory(2, user=self.user1, room=room)
        existing_messages_ids = [msg.pk for msg in messages]

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
            response = await self.delete_messages(communicator1, existing_messages_ids + [0])
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to the second user

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
            self.assertTrue(response['errors'])
            self.assertIsNone(response['data'])

            existing_messages_num = await Message.objects.filter(id__in=existing_messages_ids).acount()
            self.assertEqual(existing_messages_num, len(messages))

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_delete_messages_does_not_delete_messages_in_other_rooms(self):
        room1, room2 = await RoomAsyncFactory(2, participants=[self.user1, self.user2])
        room2_messages = await MessageAsyncFactory(2, user=self.user1, room=room2)
        messages_ids = [msg.pk for msg in room2_messages]

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

        async with join_room_communal([communicator1, communicator2], room1.pk):
            # try to delete messages in room2
            response = await self.delete_messages(communicator1, messages_ids)
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to the second user

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

            messages_exist = await Message.objects.filter(id__in=messages_ids).aexists()
            self.assertTrue(messages_exist)

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_delete_messages_with_attachments(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])
        message = await MessageAsyncFactory(
            user=self.user1, room=room, has_attachments=True, attachments__file=''
        )
        attachments_ids = message.attachments.values_list('pk', flat=True)

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
            response = await self.delete_messages(communicator, [message.pk])

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            # check that attachments were deleted
            self.assertFalse(
                await MessageAttachment.objects.filter(id__in=attachments_ids).aexists()
            )

        await communicator.disconnect()
