import factory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from core.apps.accounts.factories import UserFactory
from core.apps.brand.factories import BrandShortFactory, MatchFactory, CollaborationFactory, LikeFactory
from core.apps.brand.models import Collaboration
from core.apps.payments.factories import SubscriptionFactory


class CollaborationCreateTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1, cls.user2 = UserFactory.create_batch(2)
        cls.auth_client1, cls.auth_client2 = APIClient(), APIClient()
        cls.auth_client1.force_authenticate(cls.user1)
        cls.auth_client2.force_authenticate(cls.user2)
        cls.brand1, cls.brand2 = BrandShortFactory.create_batch(2, user=factory.Iterator([cls.user1, cls.user2]))

        SubscriptionFactory.create_batch(2, brand=factory.Iterator([cls.brand1, cls.brand2]))

        cls.match = MatchFactory(initiator=cls.brand1, target=cls.brand2)
        cls.collaboration_data = {
            **factory.build(dict, FACTORY_CLASS=CollaborationFactory, reporter=None, collab_with=None, match=None),
            'match': cls.match.pk,
        }
        del cls.collaboration_data['reporter']
        del cls.collaboration_data['collab_with']

        cls.url = reverse('collaboration')

    def test_cannot_collaborate_with_yourself(self):
        # it's not possible to make match with yourself using API,
        # but this is in the case of a random creation of such thing
        match_with_self = MatchFactory(initiator=self.brand1, target=self.brand1)
        collaboration_data = {**self.collaboration_data, 'match': match_with_self.id}

        response = self.auth_client1.post(self.url, collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collaboration_create_match_does_not_exist(self):
        collaboration_data = {**self.collaboration_data, 'match': 0}

        response = self.auth_client1.post(self.url, collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collaboration_create_with_brand_without_match(self):
        like = LikeFactory(initiator=self.brand1)

        collaboration_data = {**self.collaboration_data, 'match': like.id}

        response = self.auth_client1.post(self.url, collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collaboration_create(self):
        response = self.auth_client1.post(self.url, self.collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        collab = Collaboration.objects.select_related('reporter', 'collab_with').get(pk=response.data['id'])

        self.assertEqual(collab.reporter.id, self.brand1.id)
        self.assertEqual(collab.collab_with.id, self.brand2.id)

        for key, value in self.collaboration_data.items():
            if key == 'match':
                self.assertEqual(getattr(collab, key).id, value)
                continue

            self.assertEqual(getattr(collab, key), value)

    def test_collaboration_create_already_reported(self):
        CollaborationFactory(reporter=self.brand1, collab_with=self.brand2)  # first collab

        response = self.auth_client1.post(self.url, self.collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collaboration_create_participant_can_report(self):
        CollaborationFactory(reporter=self.brand1, collab_with=self.brand2)  # collab of the initiator

        response = self.auth_client2.post(self.url, self.collaboration_data)  # collab of the participant

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        collab = Collaboration.objects.select_related('reporter', 'collab_with').get(pk=response.data['id'])

        self.assertEqual(collab.reporter.id, self.brand2.id)
        self.assertEqual(collab.collab_with.id, self.brand1.id)

        for key, value in self.collaboration_data.items():
            if key == 'match':
                self.assertEqual(getattr(collab, key).id, value)
                continue

            self.assertEqual(getattr(collab, key), value)

    def test_collaboration_create_unauthenticated_not_allowed(self):
        response = self.client.post(self.url, self.collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_collaboration_create_wo_brand_not_allowed(self):
        user = UserFactory()
        no_brand_auth_client = APIClient()
        no_brand_auth_client.force_authenticate(user)

        response = no_brand_auth_client.post(self.url, self.collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_collaboration_create_wo_active_sub_not_allowed(self):
        user_wo_active_sub = UserFactory()
        client_wo_active_sub = APIClient()
        client_wo_active_sub.force_authenticate(user_wo_active_sub)

        BrandShortFactory(user=user_wo_active_sub)

        response = client_wo_active_sub.post(self.url, self.collaboration_data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
