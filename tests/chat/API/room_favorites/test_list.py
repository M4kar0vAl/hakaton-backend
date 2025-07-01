import factory
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.apps.accounts.factories import UserFactory
from core.apps.chat.factories import RoomFactory, RoomFavoritesFactory, MessageFactory
from core.apps.chat.models import Room
from tests.factories import APIClientFactory


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class RoomFavoritesListTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.auth_client = APIClientFactory(user=cls.user)

        cls.rooms = RoomFactory.create_batch(
            3, type=factory.Iterator([Room.MATCH, Room.INSTANT, Room.SUPPORT])
        )
        cls.match_room, cls.instant_room, cls.support_room = cls.rooms

        cls.match_room_fav, cls.instant_room_fav, cls.support_room_fav = RoomFavoritesFactory.create_batch(
            3, user=cls.user, room=factory.Iterator(cls.rooms)
        )

        cls.url = reverse('chat_favorites-list')

    def test_room_favorites_list_unauthenticated_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_room_favorites_list(self):
        room = RoomFactory(participants=[self.user])

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        self.assertEqual(len(results), len(self.rooms))

        # check that list excludes rooms that are not marked as "favorite"
        self.assertFalse([i for i in results if i['room']['id'] == room.id])

    def test_room_favorites_list_exclude_other_users_favs(self):
        another_user = UserFactory()
        room = RoomFactory(participants=[self.user, another_user])

        # none of these favs must appear in self.user results list
        another_favs = RoomFavoritesFactory.create_batch(
            2, user=another_user, room=factory.Iterator([room, self.match_room])
        )

        response = self.auth_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        self.assertEqual(len(results), len(self.rooms))

        # check that another user's favs don't appear in current user results
        self.assertFalse([i for i in results if i['id'] in set(another_favs)])

    def test_room_favorites_list_includes_last_message_attachments(self):
        message = MessageFactory(user=self.user, room=self.match_room, has_attachments=True)
        attachments_ids = [a.pk for a in message.attachments.all()]

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
