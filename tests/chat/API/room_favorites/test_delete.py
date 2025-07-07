from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.chat.factories import RoomFactory, RoomFavoritesFactory
from core.apps.chat.models import RoomFavorites
from tests.factories import APIClientFactory


class RoomFavoritesDeleteTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClientFactory(user=cls.user)

        cls.room = RoomFactory()
        cls.room_fav = RoomFavoritesFactory(user=cls.user, room=cls.room)

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
        another_room_fav = RoomFavoritesFactory(room=self.room)
        another_room_fav_url = reverse(self.view_name, kwargs={'pk': another_room_fav.pk})

        response = self.auth_client.delete(another_room_fav_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # check that it wasn't deleted
        self.assertTrue(RoomFavorites.objects.filter(pk=another_room_fav.pk).exists())
