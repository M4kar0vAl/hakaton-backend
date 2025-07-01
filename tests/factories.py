import factory
from rest_framework.test import APIClient


class APIClientFactory(factory.Factory):
    """
    Utility factory to create APIClient instances.
    Provides 'user' post generation hook to force authenticate a user.

    If you don't want the user to be authenticated simply don't pass it to the factory.
    """
    class Meta:
        model = APIClient

    @factory.post_generation
    def user(self, create, extracted, **kwargs):
        """
        Pass user to force authenticate it for current APIClient
        """
        if not create or not extracted:
            return

        self.force_authenticate(extracted)
