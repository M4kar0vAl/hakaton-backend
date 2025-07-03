import factory
from django.test import TestCase, override_settings

from core.apps.accounts.factories import UserFactory
from core.apps.chat.factories import RoomFactory
from core.apps.chat.models import Room
from core.apps.chat.tasks import empty_rooms_cleanup


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPOGATES=True
)
class EmptyRoomsCleanupTaskTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = UserFactory.create_batch(2)
        room_types = [Room.MATCH, Room.INSTANT, Room.SUPPORT]

        cls.match_room, cls.instant_room, cls.support_room = RoomFactory.create_batch(
            3,
            type=factory.Iterator(room_types),
            participants=factory.Iterator([cls.users, cls.users, [cls.users[0]]])
        )
        cls.empty_match_room, cls.empty_instant_room, cls.empty_support_room = RoomFactory.create_batch(
            3, type=factory.Iterator(room_types)
        )

        cls.task = empty_rooms_cleanup

    def test_empty_rooms_cleanup_task(self):
        self.task.delay()

        # check that non-empty rooms remain
        self.assertTrue(Room.objects.filter(pk=self.match_room.pk).exists())
        self.assertTrue(Room.objects.filter(pk=self.instant_room.pk).exists())
        self.assertTrue(Room.objects.filter(pk=self.support_room.pk).exists())

        # check that empty rooms were deleted
        self.assertFalse(Room.objects.filter(pk=self.empty_match_room.pk).exists())
        self.assertFalse(Room.objects.filter(pk=self.empty_instant_room.pk).exists())
        self.assertFalse(Room.objects.filter(pk=self.empty_support_room.pk).exists())
