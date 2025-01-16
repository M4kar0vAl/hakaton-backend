import json
import unittest
from contextlib import contextmanager

from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.db import connections
from django.test.utils import CaptureQueriesContext

User = get_user_model()


class AssertNumQueriesLessThanMixin(unittest.TestCase):
    @contextmanager
    def assertNumQueriesLessThan(self, value, using='default', verbose=False):
        with CaptureQueriesContext(connections[using]) as context:
            yield  # your test will be run here
        if verbose:
            msg = "\r\n%s" % json.dumps(context.captured_queries, indent=4)
        else:
            msg = None
        self.assertLess(len(context.captured_queries), value, msg=msg)


class BaseConsumerActionsMixin:
    async def list_(self, communicator: WebsocketCommunicator):
        response = await self._send_json_to_consumer(
            communicator=communicator,
            json_={
                'action': 'list',
                'request_id': 1500000
            }
        )

        return response

    async def join_room(self, communicator: WebsocketCommunicator, room_pk: int):
        response = await self._send_json_to_consumer(
            communicator=communicator,
            json_={
                'action': 'join_room',
                'room_pk': room_pk,
                'request_id': 1500000
            }
        )

        return response

    async def leave_room(self, communicator: WebsocketCommunicator):
        response = await self._send_json_to_consumer(
            communicator=communicator,
            json_={
                'action': 'leave_room',
                'request_id': 1500000
            }
        )

        return response

    async def get_room_messages(self, communicator: WebsocketCommunicator, page: int):
        response = await self._send_json_to_consumer(
            communicator=communicator,
            json_={
                'action': 'get_room_messages',
                'page': page,
                'request_id': 1500000
            }
        )

        return response

    async def create_message(self, communicator: WebsocketCommunicator, msg_text: str):
        response = await self._send_json_to_consumer(
            communicator=communicator,
            json_={
                'action': 'create_message',
                'msg_text': msg_text,
                'request_id': 1500000
            }
        )

        return response

    async def edit_message(self, communicator: WebsocketCommunicator, msg_id: int, edited_msg_text: str):
        response = await self._send_json_to_consumer(
            communicator=communicator,
            json_={
                'action': 'edit_message',
                'msg_id': msg_id,
                'edited_msg_text': edited_msg_text,
                'request_id': 1500000
            }
        )

        return response

    async def delete_messages(self, communicator: WebsocketCommunicator, msg_id_list: list[int]):
        response = await self._send_json_to_consumer(
            communicator=communicator,
            json_={
                'action': 'delete_messages',
                'msg_id_list': msg_id_list,
                'request_id': 1500000
            }
        )

        return response

    async def get_support_room(self, communicator: WebsocketCommunicator):
        response = await self._send_json_to_consumer(
            communicator=communicator,
            json_={
                'action': 'get_support_room',
                'request_id': 1500000
            }
        )

        return response

    async def _send_json_to_consumer(self, communicator: WebsocketCommunicator, json_: dict):
        await communicator.send_json_to(json_)

        response = await communicator.receive_json_from()

        return response


class RoomConsumerActionsMixin(BaseConsumerActionsMixin):
    pass


class AdminRoomConsumerActionsMixin(BaseConsumerActionsMixin):
    pass
