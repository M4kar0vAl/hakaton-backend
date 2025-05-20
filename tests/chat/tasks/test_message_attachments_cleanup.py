from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F
from django.test import TestCase, override_settings

from core.apps.chat.models import Message, Room, MessageAttachment
from core.apps.chat.tasks import message_attachments_cleanup

User = get_user_model()


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPOGATES=True
)
class MessageAttachmentCleanupTaskTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='user1@example.com',
            phone='+79993332211',
            fullname='Юзеров Юзер Юзерович',
            password='Pass!234',
            is_active=True
        )

        cls.room = Room.objects.create(type=Room.SUPPORT)
        cls.message = Message.objects.create(text='test', user=cls.user, room=cls.room)

        linked_attachments = MessageAttachment.objects.bulk_create([
            MessageAttachment(file='test', message=cls.message),
            MessageAttachment(file='test', message=cls.message),
        ])

        dangling_attachments = MessageAttachment.objects.bulk_create([
            MessageAttachment(file='test'),
            MessageAttachment(file='test'),
        ])

        cls.linked_attachment_id, cls.linked_attachment_expired_lifetime_id = map(lambda x: x.id, linked_attachments)
        cls.dangling_attachment_id, cls.dangling_attachment_expired_lifetime_id = map(lambda x: x.id,
                                                                                      dangling_attachments)

        # make chosen attachments expired
        MessageAttachment.objects.filter(
            id__in=[cls.linked_attachment_expired_lifetime_id, cls.dangling_attachment_expired_lifetime_id]
        ).update(
            created_at=F('created_at') - settings.MESSAGE_ATTACHMENT_DANGLING_LIFE_TIME
        )

        cls.task = message_attachments_cleanup

    def test_message_attachment_cleanup_task(self):
        self.task.delay()

        # check that all attachments that must remain actually remain
        self.assertEqual(
            MessageAttachment.objects.filter(
                id__in=[
                    self.linked_attachment_id,
                    self.linked_attachment_expired_lifetime_id,
                    self.dangling_attachment_id
                ]
            ).count(),
            3
        )

        # check that all attachments that must be deleted are actually deleted
        self.assertFalse(
            MessageAttachment.objects.filter(
                id__in=[self.dangling_attachment_expired_lifetime_id]
            ).exists()
        )
