from typing import Type, Optional

from asgiref.sync import sync_to_async
from factory import Factory


def factory_sync_to_async(factory_class: Type[Factory]):
    """
    Wraps factories with sync_to_async.

    Usage:
        # factories.py
        UserAsyncFactory = factory_sync_to_async(UserFactory)

        # tests.py
        async def test_func():
            await UserAsyncFactory(**kwargs)  # single object
            await UserAsyncFactory(size, **kwargs)  # multiple objects just like create_batch
    """

    def wrapper(size: Optional[int] = None, **kwargs):
        if size is not None:
            return sync_to_async(factory_class.create_batch)(size, **kwargs)

        return sync_to_async(factory_class)(**kwargs)

    return wrapper
