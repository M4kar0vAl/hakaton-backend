from cities_light.models import Country, City
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.test import override_settings, TransactionTestCase, tag
from django.utils import timezone
from rest_framework import status

from core.apps.blacklist.models import BlackList
from core.apps.brand.models import Category, Brand, Match
from core.apps.chat.consumers import RoomConsumer, AdminRoomConsumer
from core.apps.chat.models import Room, Message, MessageAttachment
from core.apps.payments.models import Tariff, Subscription
from tests.mixins import RoomConsumerActionsMixin
from tests.utils import get_websocket_communicator_for_user, join_room_communal, join_room

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)
@tag('slow', 'chats')
class RoomConsumerDeleteMessagesTestCase(TransactionTestCase, RoomConsumerActionsMixin):
    serialized_rollback = True

    def setUp(self):
        self.user1 = User.objects.create_user(
            email=f'user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        self.user2 = User.objects.create_user(
            email=f'user2@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        country = Country.objects.create(name='Country', continent='EU')
        city = City.objects.create(name='City', country=country)

        self.brand_data = {
            'tg_nickname': '@asfhbnaf',
            'city': city,
            'name': 'brand1',
            'position': 'position',
            'category': Category.objects.get(id=1),
            'subs_count': 10000,
            'avg_bill': 10000,
            'uniqueness': 'uniqueness',
            'logo': 'string',
            'photo': 'string'
        }

        self.brand1 = Brand.objects.create(user=self.user1, **self.brand_data)
        self.brand2 = Brand.objects.create(user=self.user2, **self.brand_data)

        now = timezone.now()
        self.tariff = Tariff.objects.get(name='Lite Match')
        self.tariff_relativedelta = self.tariff.get_duration_as_relativedelta()

        Subscription.objects.bulk_create([
            Subscription(
                brand=brand,
                tariff=self.tariff,
                start_date=now,
                end_date=now + self.tariff_relativedelta,
                is_active=True
            )
            for brand in [self.brand1, self.brand2]
        ])

        self.path = 'ws/chat/'
        self.accepted_protocol = 'chat'

        self.admin_path = 'ws/admin-chat/'
        self.admin_accepted_protocol = 'admin-chat'

    async def test_delete_messages_wo_active_sub_not_allowed(self):
        user_wo_active_sub = await User.objects.acreate(
            email=f'user3@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        brand = await Brand.objects.acreate(user=user_wo_active_sub, **self.brand_data)

        room = await Room.objects.acreate(type=Room.INSTANT)
        await room.participants.aset([user_wo_active_sub])

        msg = await Message.objects.acreate(
            text='test',
            user=user_wo_active_sub,
            room=room
        )

        now = timezone.now()

        # create active sub
        sub = await Subscription.objects.acreate(
            brand=brand,
            tariff=self.tariff,
            start_date=now,
            end_date=now + self.tariff_relativedelta,
            is_active=True
        )

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
            # make sub expired
            sub.end_date = now - relativedelta(days=1)
            await sub.asave()

            response = await self.delete_messages(communicator, [msg.id])

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)

        await communicator.disconnect()

    async def test_delete_messages_not_in_room_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        message = await Message.objects.acreate(
            text='asf',
            user=self.user1,
            room=room
        )

        communicator = get_websocket_communicator_for_user(
            url_pattern=self.path,
            path=self.path,
            consumer_class=RoomConsumer,
            protocols=[self.accepted_protocol],
            user=self.user1
        )

        connected, _ = await communicator.connect()

        self.assertTrue(connected)

        response = await self.delete_messages(communicator, [message.id])

        await communicator.disconnect()

        self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])

        msg_exists = await Message.objects.filter(id=message.id).aexists()

        self.assertTrue(msg_exists)

    async def test_delete_messages_if_brand_in_blacklist_of_interlocutor_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        msg = await Message.objects.acreate(
            text='asf',
            user=self.user1,
            room=room
        )

        # brand2 blocks brand1
        await BlackList.objects.acreate(initiator=self.brand2, blocked=self.brand1)

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
            response = await self.delete_messages(communicator, [msg.id])

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_delete_messages_if_interlocutor_in_blacklist_of_brand_not_allowed(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        msg = await Message.objects.acreate(
            text='asf',
            user=self.user1,
            room=room
        )

        # brand1 blocks brand2
        await BlackList.objects.acreate(initiator=self.brand1, blocked=self.brand2)

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
            response = await self.delete_messages(communicator, [msg.id])

            self.assertEqual(response['response_status'], status.HTTP_403_FORBIDDEN)
            self.assertIsNone(response['data'])
            self.assertTrue(response['errors'])

        await communicator.disconnect()

    async def test_delete_messages_all_not_found(self):
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        await Message.objects.acreate(
            text='asf',
            user=self.user1,
            room=room
        )

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
        connected2, __ = await communicator2.connect()

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
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT),
            Room(type=Room.SUPPORT),
        ])

        match_room, instant_room, support_room = rooms

        await match_room.participants.aset([self.user1, self.user2])
        await instant_room.participants.aset([self.user1, self.user2])
        await support_room.participants.aset([self.user1])

        await Match.objects.acreate(
            initiator=self.user1.brand,
            target=self.user2.brand,
            is_match=False,
            room=instant_room
        )

        messages = await Message.objects.abulk_create([
                                                          Message(
                                                              text='asf',
                                                              user=self.user1,
                                                              room=room
                                                          )
                                                          for room in rooms
                                                      ] + [
                                                          Message(
                                                              text='fahnj',
                                                              user=self.user1,
                                                              room=room
                                                          )
                                                          for room in rooms
                                                      ])

        match_room_messages_ids = [msg.id for msg in messages if msg.room_id == match_room.id]
        instant_room_messages_ids = [msg.id for msg in messages if msg.room_id == instant_room.id]
        support_room_messages_ids = [msg.id for msg in messages if msg.room_id == support_room.id]

        # initial admin (that was before the user connected to websocket)
        admin1 = await User.objects.acreate(
            email=f'admin_unique@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True,
            is_staff=True
        )

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
        connected2, __ = await communicator2.connect()
        connected3, ___ = await admin_communicator1.connect()

        self.assertTrue(connected1)
        self.assertTrue(connected2)
        self.assertTrue(connected3)

        # create another admin when user is already connected
        # admin2 must be added to the list of groups to which the message is sent
        admin2 = await User.objects.acreate(
            email=f'admin2_unique@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True,
            is_staff=True
        )

        admin_communicator2 = get_websocket_communicator_for_user(
            url_pattern=self.admin_path,
            path=self.admin_path,
            consumer_class=AdminRoomConsumer,
            protocols=[self.admin_accepted_protocol],
            user=admin2
        )

        connected4, __ = await admin_communicator2.connect()

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
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        messages = await Message.objects.abulk_create([
            Message(
                text='asf',
                user=self.user2,
                room=room
            ),
            Message(
                text='fahnj',
                user=self.user2,
                room=room
            )
        ])

        messages_ids = [msg.id for msg in messages]

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
        connected2, __ = await communicator2.connect()

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
        room = await Room.objects.acreate(type=Room.MATCH)

        await room.participants.aset([self.user1, self.user2])

        messages = await Message.objects.abulk_create([
            Message(
                text='asf',
                user=self.user1,
                room=room
            ),
            Message(
                text='fahnj',
                user=self.user1,
                room=room
            )
        ])

        existing_messages_ids = [msg.id for msg in messages]

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
        connected2, __ = await communicator2.connect()

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
        rooms = await Room.objects.abulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.MATCH)
        ])

        room1, room2 = rooms

        await room1.participants.aset([self.user1, self.user2])
        await room2.participants.aset([self.user1, self.user2])

        room2_messages = await Message.objects.abulk_create([
            Message(
                text='fahnj',
                user=self.user1,
                room=room2
            ),
            Message(
                text='fahnj',
                user=self.user1,
                room=room2
            )
        ])

        messages_ids = [msg.id for msg in room2_messages]

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
        connected2, __ = await communicator2.connect()

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
        room = await Room.objects.acreate(type=Room.MATCH)
        await room.participants.aset([self.user1, self.user2])

        message = await Message.objects.acreate(
            text='fahnj',
            user=self.user1,
            room=room
        )

        attachments = await MessageAttachment.objects.abulk_create([
            MessageAttachment(file='file1', message=message),
            MessageAttachment(file='file2', message=message)
        ])
        attachments_ids = [a.id for a in attachments]

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
            response = await self.delete_messages(communicator, [message.id])

            self.assertEqual(response['response_status'], status.HTTP_200_OK)

            # check that attachments were deleted
            self.assertFalse(
                await MessageAttachment.objects.filter(id__in=attachments_ids).aexists()
            )

        await communicator.disconnect()
