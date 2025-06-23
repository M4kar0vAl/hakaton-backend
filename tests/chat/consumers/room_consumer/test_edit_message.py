import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.blacklist.factories import BlackListAsyncFactory
from core.apps.brand.factories import (
    BrandShortFactory,
    MatchAsyncFactory
)
from core.apps.chat.factories import RoomAsyncFactory, MessageAsyncFactory
from core.apps.chat.models import Room, Message
from core.apps.payments.factories import SubscriptionFactory, SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import (
    join_room_communal,
    join_room,
    get_user_communicator,
    get_admin_communicator
)


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class RoomConsumerEditMessageTestCase(TransactionTestCase, RoomConsumerActionsMixin):

    def setUp(self):
        self.user1, self.user2 = UserFactory.create_batch(2)
        self.brand1, self.brand2 = BrandShortFactory.create_batch(2, user=factory.Iterator([self.user1, self.user2]))

        SubscriptionFactory.create_batch(2, brand=factory.Iterator([self.brand1, self.brand2]))

    async def test_edit_message_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        room = await RoomAsyncFactory(participants=[user_wo_active_sub])
        msg = await MessageAsyncFactory(user=user_wo_active_sub, room=room)
        sub = await SubscriptionAsyncFactory(brand__user=user_wo_active_sub)  # create active sub

        communicator = get_user_communicator(user_wo_active_sub)

        # connect with active sub
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            # make sub inactive
            sub.is_active = False
            await sub.asave()

            response = await self.edit_message(communicator, msg.pk, 'edited')
            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

        await communicator.disconnect()

    async def test_edit_message_not_in_room_not_allowed(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])
        message = await MessageAsyncFactory(user=self.user1, room=room)

        communicator = get_user_communicator(self.user1)

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await self.edit_message(communicator, message.pk, 'edited')
        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        # check that message text did not change
        msg = await Message.objects.aget(id=message.pk)
        self.assertEqual(msg.text, message.text)

    async def test_edit_message_if_brand_in_blacklist_of_interlocutor_not_allowed(self):
        room = await RoomAsyncFactory(type=Room.MATCH, participants=[self.user1, self.user2])
        msg = await MessageAsyncFactory(user=self.user1, room=room)
        await BlackListAsyncFactory(initiator=self.brand2, blocked=self.brand1)  # brand2 blocks brand1

        communicator = get_user_communicator(self.user1)

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            response = await self.edit_message(communicator, msg.pk, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_edit_message_if_interlocutor_in_blacklist_of_brand_not_allowed(self):
        room = await RoomAsyncFactory(type=Room.MATCH, participants=[self.user1, self.user2])
        msg = await MessageAsyncFactory(user=self.user1, room=room)
        await BlackListAsyncFactory(initiator=self.brand1, blocked=self.brand2)  # brand1 blocks brand2

        communicator = get_user_communicator(self.user1)

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        async with join_room(communicator, room.pk):
            response = await self.edit_message(communicator, msg.pk, 'test')

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_edit_message_not_found(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])

        communicator1 = get_user_communicator(self.user1)
        communicator2 = get_user_communicator(self.user2)

        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        async with join_room_communal([communicator1, communicator2], room.pk):
            response = await self.edit_message(communicator1, 0, 'edited')
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to second user

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_edit_message(self):
        both_users = [self.user1, self.user2]
        rooms = await RoomAsyncFactory(
            3,
            type=factory.Iterator([Room.MATCH, Room.INSTANT, Room.SUPPORT]),
            participants=factory.Iterator([both_users, both_users, [self.user1]])
        )
        match_room, instant_room, support_room = rooms

        await MatchAsyncFactory(instant_coop=True, initiator=self.brand1, target=self.brand2, room=instant_room)

        match_room_msg, instant_room_msg, support_room_msg = await MessageAsyncFactory(
            3, user=self.user1, room=factory.Iterator(rooms)
        )

        # initial admin (that was before the user connected to websocket)
        admin1 = await UserAsyncFactory(admin=True)

        communicator1 = get_user_communicator(self.user1)
        communicator2 = get_user_communicator(self.user2)
        admin_communicator1 = get_admin_communicator(admin1)

        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        connected3, _ = await admin_communicator1.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)
        self.assertTrue(connected3)

        # create another admin when user is already connected
        # admin2 must be added to the list of groups to which the message is sent
        admin2 = await UserAsyncFactory(admin=True)

        admin_communicator2 = get_admin_communicator(admin2)

        connected4, _ = await admin_communicator2.connect()
        self.assertTrue(connected4)

        async with join_room_communal([communicator1, communicator2], match_room.pk):
            edited_msg_text = 'edited'
            response1 = await self.edit_message(communicator1, match_room_msg.pk, edited_msg_text)
            response2 = await communicator2.receive_json_from()

            # check that admins aren't notified about non-support room actions
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response1, response2]:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)
                self.assertEqual(response['data']['id'], match_room_msg.pk)
                self.assertEqual(response1['data']['text'], edited_msg_text)

            msg = await Message.objects.aget(pk=match_room_msg.pk)
            self.assertEqual(msg.text, edited_msg_text)  # check that message text changed in db

        async with join_room_communal([communicator1, communicator2], instant_room.pk):
            edited_msg_text = 'edited'
            response1 = await self.edit_message(communicator1, instant_room_msg.pk, edited_msg_text)
            response2 = await communicator2.receive_json_from()

            # check that admins aren't notified about non-support room actions
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response1, response2]:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)
                self.assertEqual(response['data']['id'], instant_room_msg.pk)
                self.assertEqual(response1['data']['text'], edited_msg_text)

        async with join_room(communicator1, support_room.pk):
            edited_msg_text = 'edited'
            response = await self.edit_message(communicator1, support_room_msg.pk, edited_msg_text)
            admin1_response = await admin_communicator1.receive_json_from()
            admin2_response = await admin_communicator2.receive_json_from()

            # check that only one notification is sent
            self.assertTrue(await communicator1.receive_nothing())
            self.assertTrue(await admin_communicator1.receive_nothing())
            self.assertTrue(await admin_communicator2.receive_nothing())

            for response in [response, admin1_response, admin2_response]:
                self.assertEqual(response['response_status'], status.HTTP_200_OK)
                self.assertEqual(response['data']['id'], support_room_msg.pk)
                self.assertEqual(response1['data']['text'], edited_msg_text)

        await communicator1.disconnect()
        await communicator2.disconnect()
        await admin_communicator1.disconnect()
        await admin_communicator2.disconnect()

    async def test_edit_message_of_another_user_not_allowed(self):
        room = await RoomAsyncFactory(participants=[self.user1, self.user2])
        message = await MessageAsyncFactory(user=self.user2, room=room)

        communicator1 = get_user_communicator(self.user1)
        communicator2 = get_user_communicator(self.user2)

        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)

        async with join_room_communal([communicator1, communicator2], room.pk):
            response = await self.edit_message(communicator1, message.pk, 'edited')
            self.assertTrue(await communicator2.receive_nothing())  # check that nothing was sent to second user

            self.assertEqual(response['response_status'], status.HTTP_404_NOT_FOUND)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator1.disconnect()
        await communicator2.disconnect()
