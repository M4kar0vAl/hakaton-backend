from contextlib import asynccontextmanager
from typing import Type, List, Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.urls import re_path
from rest_framework_simplejwt.tokens import Token, AccessToken

from core.apps.chat.consumers import RoomConsumer, AdminRoomConsumer
from core.apps.chat.middleware import JwtAuthMiddlewareStack
from core.apps.chat.utils import channels_reverse

User = get_user_model()


def get_websocket_application(
        url_pattern: str,
        consumer_class: Type[AsyncJsonWebsocketConsumer]
):
    app = JwtAuthMiddlewareStack(URLRouter([
        re_path(url_pattern, consumer_class.as_asgi())
    ]))

    return app


def get_websocket_communicator(
        url_pattern: str,
        path: str,
        consumer_class: Type[AsyncJsonWebsocketConsumer],
        protocols: list[str],
        token: str | Token | None = None
) -> WebsocketCommunicator:
    """
    Construct websocket communicator.

    Should be used in consumer tests.

    Args:
        url_pattern: url pattern for consumer
        path: path, including url kwargs
        consumer_class: consumer to be tested
        protocols: list of subprotocols for handshake
        token: access token to authenticate user

    Returns:
        WebsocketCommunicator instance
    """
    protocols_ = f"{', '.join(protocols)}"

    if token is not None:
        protocols_ += f', {token}' if protocols_ else f'{token}'

    app = get_websocket_application(url_pattern, consumer_class)

    communicator = WebsocketCommunicator(
        app,
        path=path,
        # middleware uses headers too, so need to specify them too
        headers=[
            (b'sec-websocket-protocol', bytes(protocols_, 'utf-8'))
        ],
        # channels automatically constructs protocols from sec-websocket-protocol header
        # BUT NOT HERE, so need to specify them manually
        subprotocols=protocols_.split(', ')
    )

    return communicator


def get_websocket_communicator_for_user(
        url_pattern: str,
        path: str,
        consumer_class: Type[AsyncJsonWebsocketConsumer],
        protocols: list[str],
        user: User
):
    access = AccessToken.for_user(user)

    communicator = get_websocket_communicator(
        url_pattern=url_pattern,
        path=path,
        consumer_class=consumer_class,
        protocols=protocols,
        token=access
    )

    return communicator


def get_user_communicator(user: User, protocols: Optional[List[str]] = None):
    """
    Get websocket communicator for user.
    Authentication is handled automatically.

    Args:
        user: user to get communicator for
        protocols: list of protocols to connect with (optional)

    Returns:
        WebsocketCommunicator instance
    """
    path_to_user_chat = channels_reverse('chat')

    communicator = get_websocket_communicator_for_user(
        url_pattern=path_to_user_chat.removeprefix('/'),
        path=path_to_user_chat,
        consumer_class=RoomConsumer,
        protocols=['chat'] if protocols is None else protocols,
        user=user
    )

    return communicator


def get_admin_communicator(user: User, protocols: Optional[List[str]] = None):
    """
    Get websocket communicator for staff or admin user.
    Authentication is handled automatically.

    Args:
        user: user to get communicator for
        protocols: list of protocols to connect with (optional)

    Returns:
        WebsocketCommunicator instance
    """
    path_to_admin_chat = channels_reverse('admin_chat')

    communicator = get_websocket_communicator_for_user(
        url_pattern=path_to_admin_chat.removeprefix('/'),
        path=path_to_admin_chat,
        consumer_class=AdminRoomConsumer,
        protocols=['admin-chat'] if protocols is None else protocols,
        user=user
    )

    return communicator


@asynccontextmanager
async def websocket_connect(communicator: WebsocketCommunicator, check_connected: bool = True):
    """
    Connect the communicator to a websocket.

    Disconnect on exit.

    Args:
        communicator: WebsocketCommunicator instance to connect
        check_connected: if True, it will check whether the communicator was connected
    """
    is_connected, subprotocol = await communicator.connect()

    if check_connected:
        # depending on whether socket was accepted or not, second return value of the connect method would change
        # https://channels.readthedocs.io/en/stable/topics/testing.html#connect
        assert is_connected, f'Connection failed. Close code: {subprotocol}'

    try:
        yield is_connected, subprotocol
    finally:
        await communicator.disconnect()


@asynccontextmanager
async def websocket_connect_communal(communicators: list[WebsocketCommunicator], check_connected: bool = True):
    """
    Connect the list of communicators to a websocket.

    Disconnect on exit.

    Args:
        communicators: list of WebsocketCommunicator instances to connect
        check_connected: if True, it will check whether each communicator was connected
    """
    response_list = []

    for i, communicator in enumerate(communicators):
        is_connected, subprotocol = await communicator.connect()

        if check_connected:
            assert is_connected, f'Communicator at index {i} was not connected. Close code: {subprotocol}'

        response_list.append((is_connected, subprotocol))

    try:
        yield response_list
    finally:
        for communicator in communicators:
            await communicator.disconnect()


@asynccontextmanager
async def _join_room(communicator: WebsocketCommunicator, room_id: int):
    await communicator.send_json_to({
        'action': 'join_room',
        'room_id': room_id,
        'request_id': 1500000
    })

    response = await communicator.receive_json_from()

    try:
        yield response
    finally:
        await communicator.send_json_to({
            'action': 'leave_room',
            'request_id': 1500000
        })

        await communicator.receive_json_from()


@asynccontextmanager
async def join_room(communicator: WebsocketCommunicator, room_id: int, connect: bool = False):
    """
    Join room and return response

    Leave room on exit

    Args:
        communicator: connected communicator for interactions with websocket application
        room_id: id of a room to join,
        connect: boolean indicating whether to connect to websocket first or not.
    """
    if connect:
        async with websocket_connect(communicator):
            async with _join_room(communicator, room_id) as response:
                yield response
    else:
        async with _join_room(communicator, room_id) as response:
            yield response


@asynccontextmanager
async def _join_room_communal(communicators: list[WebsocketCommunicator], room_id: int):
    """
    Context manager for connecting several communicators to one room.

    On exit leaves the room for each communicator

    Args:
        communicators: list of communicators for joining the room
        room_id: id of the room to be connected to

    Returns:
        list of responses of calling join room for each communicator, preserving the order
    """
    responses = []

    for communicator in communicators:
        await communicator.send_json_to({
            'action': 'join_room',
            'room_id': room_id,
            'request_id': 1500000
        })

        response = await communicator.receive_json_from()
        responses.append(response)

    try:
        yield responses
    finally:
        for communicator in communicators:
            await communicator.send_json_to({
                'action': 'leave_room',
                'request_id': 1500000
            })

            await communicator.receive_json_from()


@asynccontextmanager
async def join_room_communal(communicators: list[WebsocketCommunicator], room_id: int, connect: bool = False):
    """
    Context manager for connecting several communicators to one room.

    On exit leaves the room for each communicator

    Args:
        communicators: list of communicators for joining the room
        room_id: id of the room to be connected to
        connect: boolean indicating whether to connect to websocket first or not.

    Returns:
        list of responses of calling join room for each communicator, preserving the order
    """
    if connect:
        async with websocket_connect_communal(communicators):
            async with _join_room_communal(communicators, room_id) as response:
                yield response
    else:
        async with _join_room_communal(communicators, room_id) as response:
            yield response
