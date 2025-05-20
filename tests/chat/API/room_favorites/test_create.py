from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.chat.models import Room, RoomFavorites, MessageAttachment, Message

User = get_user_model()


class RoomFavoritesCreateTestCase(APITestCase):
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

        cls.room = Room.objects.create(type=Room.MATCH)

        cls.url = reverse('chat_favorites-list')

    def test_room_favorites_create_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, {'room': self.room.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_room_favorites_create(self):
        response = self.auth_client.post(self.url, {'room': self.room.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        room_data = response.data['room']

        # check that room in response has last message and interlocutors keys
        self.assertTrue('last_message' in room_data)
        self.assertTrue('interlocutors' in room_data)

        room_fav_id = response.data['id']

        try:
            room_fav = RoomFavorites.objects.get(id=room_fav_id)
        except RoomFavorites.DoesNotExist:
            room_fav = None

        # check that instance was created in db
        self.assertIsNotNone(room_fav)
        self.assertEqual(room_fav.user_id, self.user.id)
        self.assertEqual(room_fav.room_id, self.room.id)

    def test_room_favorites_create_cannot_add_the_same_room(self):
        self.auth_client.post(self.url, {'room': self.room.id})  # add room to the favorites
        response = self.auth_client.post(self.url, {'room': self.room.id})  # try to add the same room again

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_room_favorites_create_includes_last_message_attachments(self):
        message = Message.objects.create(
            text='asdaw',
            user=self.user,
            room=self.room
        )

        attachments = MessageAttachment.objects.bulk_create([
            MessageAttachment(file='file1', message=message),
            MessageAttachment(file='file2', message=message),
        ])
        attachments_ids = [a.id for a in attachments]

        response = self.auth_client.post(self.url, {'room': self.room.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        last_message = response.data['room']['last_message']
        self.assertTrue('attachments' in last_message)

        response_attachments_ids = [a['id'] for a in last_message['attachments']]
        self.assertEqual(response_attachments_ids, attachments_ids)
