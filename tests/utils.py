from typing import Type

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.urls import re_path
from rest_framework_simplejwt.tokens import Token

from core.apps.chat.middleware import JwtAuthMiddlewareStack


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
    protocols_ = f'{', '.join(protocols)}'

    if token is not None:
        protocols_ += f', {token}'

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
