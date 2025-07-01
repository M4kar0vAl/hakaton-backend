import factory
from django.test import override_settings, TransactionTestCase, tag
from rest_framework import status

from core.apps.accounts.factories import UserFactory, UserAsyncFactory
from core.apps.blacklist.factories import BlackListAsyncFactory
from core.apps.brand.factories import (
    BrandShortFactory,
    MatchAsyncFactory
)
from core.apps.chat.factories import (
    RoomAsyncFactory,
    MessageAsyncFactory,
    MessageAttachmentAsyncFactory
)
from core.apps.chat.models import Room, MessageAttachment
from core.apps.payments.factories import SubscriptionAsyncFactory
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import (
    join_room_communal,
    join_room,
    get_user_communicator,
    get_admin_communicator,
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
class RoomConsumerCreateMessageTestCase(TransactionTestCase, RoomConsumerActionsMixin):

    def setUp(self):
        self.user1, self.user2 = UserFactory.create_batch(2)
        self.brand1, self.brand2 = BrandShortFactory.create_batch(
            2, user=factory.Iterator([self.user1, self.user2]), has_sub=True
        )

    async def test_create_message_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await UserAsyncFactory()
        room = await RoomAsyncFactory(participants=[user_wo_active_sub])

        # create active sub
        # users can connect to consumer only with active sub
        sub = await SubscriptionAsyncFactory(brand__user=user_wo_active_sub)

        communicator = get_user_communicator(user_wo_active_sub)

        async with join_room(communicator, room.pk, connect=True):
            # deactivate sub for create_message action test
            sub.is_active = False
            await sub.asave()

            response = await self.create_message(communicator, 'test')

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

    async def test_create_message_not_in_room_not_allowed(self):
        communicator = get_user_communicator(self.user1)

        async with websocket_connect(communicator):
            response = await self.create_message(communicator, 'asf')

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_create_message_if_brand_in_blacklist_of_interlocutor_not_allowed(self):
        room = await RoomAsyncFactory(type=Room.MATCH, participants=[self.user1, self.user2])
        await BlackListAsyncFactory(initiator=self.brand2, blocked=self.brand1)  # brand2 blocks brand1

        communicator = get_user_communicator(self.user1)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.create_message(communicator, 'test')

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_create_message_if_interlocutor_in_blacklist_of_brand_not_allowed(self):
        room = await RoomAsyncFactory(type=Room.MATCH, participants=[self.user1, self.user2])
        await BlackListAsyncFactory(initiator=self.brand1, blocked=self.brand2)  # brand1 blocks brand2

        communicator = get_user_communicator(self.user1)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.create_message(communicator, 'test')

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_create_message(self):
        both_users = [self.user1, self.user2]
        match_room, instant_room, support_room = await RoomAsyncFactory(
            3,
            type=factory.Iterator([Room.MATCH, Room.INSTANT, Room.SUPPORT]),
            participants=factory.Iterator([both_users, both_users, [self.user1]])
        )

        await MatchAsyncFactory(instant_coop=True, initiator=self.brand1, target=self.brand2, room=instant_room)

        # initial admin (that was before the user connected to websocket)
        admin1 = await UserAsyncFactory(admin=True)

        communicator1 = get_user_communicator(self.user1)
        communicator2 = get_user_communicator(self.user2)
        admin_communicator1 = get_admin_communicator(admin1)

        async with websocket_connect_communal([communicator1, communicator2, admin_communicator1]):
            # create another admin when user is already connected
            # admin2 must be added to the list of groups to which the message is sent
            admin2 = await UserAsyncFactory(admin=True)
            admin_communicator2 = get_admin_communicator(admin2)

            async with websocket_connect(admin_communicator2):
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

    async def test_create_message_instant_room_not_allowed_if_message_by_user_already_created(self):
        room = await RoomAsyncFactory(type=Room.INSTANT, participants=[self.user1, self.user2])
        await MatchAsyncFactory(instant_coop=True, initiator=self.brand1, target=self.brand2, room=room)
        await MessageAsyncFactory(user=self.user1, room=room)

        communicator = get_user_communicator(self.user1)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.create_message(communicator, 'asf')

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_create_message_in_instant_room_user_is_not_the_initiator_of_coop(self):
        room = await RoomAsyncFactory(type=Room.INSTANT, participants=[self.user1, self.user2])
        await MatchAsyncFactory(instant_coop=True, initiator=self.brand1, target=self.brand2, room=room)

        communicator = get_user_communicator(self.user2)

        async with join_room(communicator, room.pk, connect=True):
            response = await self.create_message(communicator, 'asf')

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

    async def test_create_message_with_attachments(self):
        room = await RoomAsyncFactory(type=Room.MATCH, participants=[self.user1, self.user2])
        attachments = await MessageAttachmentAsyncFactory(2)
        attachments_ids = [a.pk for a in attachments]

        communicator1 = get_user_communicator(self.user1)
        communicator2 = get_user_communicator(self.user2)

        async with join_room_communal([communicator1, communicator2], room.pk, connect=True):
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
