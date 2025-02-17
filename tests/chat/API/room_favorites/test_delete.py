from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.chat.models import Room, RoomFavorites

User = get_user_model()


class RoomFavoritesDeleteTestCase(APITestCase):
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

        cls.room_fav = RoomFavorites.objects.create(user=cls.user, room=cls.room)

        cls.view_name = 'chat_favorites-detail'
        cls.url = reverse(cls.view_name, kwargs={'pk': cls.room_fav.pk})

    def test_room_favorites_delete_unauthenticated_not_allowed(self):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_room_favorites_delete(self):
        response = self.auth_client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertIsNone(response.data)
        self.assertFalse(RoomFavorites.objects.filter(pk=self.room_fav.pk).exists())

    def test_room_favorites_delete_not_existing(self):
        not_existing_url = reverse(self.view_name, kwargs={'pk': 0})

        response = self.auth_client.delete(not_existing_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertTrue(self.user.room_favorites.exists())

    def test_room_favorites_delete_fav_of_another_user_not_found(self):
        another_user = User.objects.create_user(
            email='user2@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        another_room_fav = RoomFavorites.objects.create(user=another_user, room=self.room)

        another_room_fav_url = reverse(self.view_name, kwargs={'pk': another_room_fav.pk})

        response = self.auth_client.delete(another_room_fav_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # check that it wasn't deleted
        self.assertTrue(RoomFavorites.objects.filter(pk=another_room_fav.pk).exists())
