from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.chat.models import Room, RoomFavorites, Message, MessageAttachment

User = get_user_model()


class RoomFavoritesListTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.auth_client = APIClient()
        cls.auth_client.force_authenticate(cls.user)

        cls.rooms = Room.objects.bulk_create([
            Room(type=Room.MATCH),
            Room(type=Room.INSTANT),
            Room(type=Room.SUPPORT),
        ])

        cls.match_room, cls.instant_room, cls.support_room = cls.rooms

        cls.match_room_fav, cls.instant_room_fav, cls.support_room_fav = RoomFavorites.objects.bulk_create([
            RoomFavorites(user=cls.user, room=room)
            for room in cls.rooms
        ])

        cls.url = reverse('chat_favorites-list')

    def test_room_favorites_list_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_room_favorites_list(self):
        room = Room.objects.create(type=Room.MATCH)
        room.participants.add(self.user)

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        self.assertEqual(len(results), len(self.rooms))

        # check that list excludes rooms that are not marked as "favorite"
        self.assertFalse([i for i in results if i['room']['id'] == room.id])

    def test_room_favorites_list_exclude_other_users_favs(self):
        another_user = User.objects.create_user(
            email='user2@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        room = Room.objects.create(type=Room.MATCH)

        # suppose that this match room is common for both users
        self.match_room.participants.set([self.user, another_user])

        # none of these favs must appear in self.user results list
        another_favs = RoomFavorites.objects.bulk_create([
            RoomFavorites(user=another_user, room=room),
            RoomFavorites(user=another_user, room=self.match_room),  # room is favorite for both users
        ])

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        self.assertEqual(len(results), len(self.rooms))

        # check that another user's favs don't appear in current user results
        self.assertFalse([i for i in results if i['id'] in set(another_favs)])

    def test_room_favorites_list_includes_last_message_attachments(self):
        message = Message.objects.create(
            text='asdaw',
            user=self.user,
            room=self.match_room
        )

        attachments = MessageAttachment.objects.bulk_create([
            MessageAttachment(file='file1', message=message),
            MessageAttachment(file='file2', message=message),
        ])
        attachments_ids = [a.id for a in attachments]

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        self.assertEqual(len(results), len(self.rooms))

        match_room_response_data = next(
            room_fav for room_fav in results if room_fav['id'] == self.match_room_fav.id
        )['room']

        last_message = match_room_response_data['last_message']
        self.assertTrue('attachments' in last_message)

        response_attachments_ids = [a['id'] for a in last_message['attachments']]
        self.assertEqual(response_attachments_ids, attachments_ids)
