from contextlib import asynccontextmanager, nullcontext
from typing import Type, List, Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.urls import re_path
from rest_framework.generics import GenericAPIView
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
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
async def join_room(communicator: WebsocketCommunicator, room_id: int, connect: bool = False):
    """
    Join room and return response

    Leave room on exit

    Args:
        communicator: connected communicator for interactions with websocket application
        room_id: id of a room to join,
        connect: boolean indicating whether to connect to websocket first or not.

    Returns:
        response of calling join_room action
    """
    # if connect is True, uses websocket_connect cm wrapper, otherwise just executes the code block
    async with websocket_connect(communicator) if connect else nullcontext():
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
async def join_room_communal(communicators: list[WebsocketCommunicator], room_id: int, connect: bool = False):
    """
    Context manager for connecting several communicators to one room.

    On exit leaves the room for each communicator

    Args:
        communicators: list of communicators for joining the room
        room_id: id of the room to be connected to
        connect: boolean indicating whether to connect to websocket first or not.

    Returns:
        list of responses of calling join_room action for each communicator, preserving the order
    """
    async with websocket_connect_communal(communicators) if connect else nullcontext():
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


def refresh_api_settings():
    """
    Update cached values on some base classes. Use when overriding REST_FRAMEWORK setting in tests.
    """
    GenericAPIView.filter_backends = api_settings.DEFAULT_FILTER_BACKENDS
    GenericAPIView.pagination_class = api_settings.DEFAULT_PAGINATION_CLASS

    APIView.renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    APIView.parser_classes = api_settings.DEFAULT_PARSER_CLASSES
    APIView.authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    APIView.throttle_classes = api_settings.DEFAULT_THROTTLE_CLASSES
    APIView.permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES
    APIView.content_negotiation_class = api_settings.DEFAULT_CONTENT_NEGOTIATION_CLASS
    APIView.metadata_class = api_settings.DEFAULT_METADATA_CLASS
    APIView.versioning_class = api_settings.DEFAULT_VERSIONING_CLASS

    APIRequestFactory.renderer_classes_list = api_settings.TEST_REQUEST_RENDERER_CLASSES
    APIRequestFactory.default_format = api_settings.TEST_REQUEST_DEFAULT_FORMAT
