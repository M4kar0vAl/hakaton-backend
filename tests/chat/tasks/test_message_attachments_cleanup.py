import factory
from django.test import TestCase, override_settings

from core.apps.chat.factories import MessageAttachmentFactory, MessageFactory, MessageAttachmentExpiredFactory
from core.apps.chat.models import MessageAttachment
from core.apps.chat.tasks import message_attachments_cleanup


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPOGATES=True
)
class MessageAttachmentCleanupTaskTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.message = MessageFactory()

        attachments = MessageAttachmentFactory.create_batch(
            2, message=factory.Iterator([cls.message, None]), file=''
        )
        expired_attachments = MessageAttachmentExpiredFactory.create_batch(
            2, message=factory.Iterator([cls.message, None]), file=''
        )

        cls.linked_attachment_id, cls.dangling_attachment_id = map(lambda x: x.id, attachments)
        cls.linked_attachment_expired_lifetime_id, cls.dangling_attachment_expired_lifetime_id = map(
            lambda x: x.id, expired_attachments
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
