from collections.abc import Iterable
from typing import Any, Optional

from channels.layers import get_channel_layer
from django.conf import settings
from django.urls import reverse

from core.common.validators import is_valid_file_type


def channels_reverse(viewname, args=None, kwargs=None):
    return reverse(viewname, urlconf=settings.CHANNELS_URLCONF, args=args, kwargs=kwargs)


async def get_payload(
        action: str,
        data: dict[str, Any] = None,
        errors: Optional[list[str]] = None,
        status: int = 200,
        request_id: int = None
) -> dict[str, Any]:
    if errors is None:
        errors = []

    payload = {
        "errors": errors,
        "data": data,
        "action": action,
        "response_status": status,
        "request_id": request_id,
    }

    return payload


async def send_to_groups(
        groups: Iterable[str],
        payload: dict[str, Any],
        handler_name: str,
        channel_layer
) -> None:
    for group in groups:
        await channel_layer.group_send(group, {'type': handler_name, 'payload': payload})


async def _reply_to_groups(
        groups: Iterable[str],
        handler_name: str,
        channel_layer,
        action: str,
        data: dict[str, Any] = None,
        errors: Optional[list[str]] = None,
        status: int = 200,
        request_id: int = None,
):
    if not isinstance(groups, Iterable):
        raise TypeError("'groups' must be an iterable")

    if not isinstance(data, dict):
        raise TypeError("'data' must be a dict")

    payload = await get_payload(
        action=action,
        data=data,
        errors=errors,
        status=status,
        request_id=request_id,
    )

    await send_to_groups(
        groups=groups,
        payload=payload,
        handler_name=handler_name,
        channel_layer=channel_layer
    )


async def reply_to_groups(
        groups: Iterable[str],
        handler_name: str,
        action: str,
        data: dict[str, Any] = None,
        errors: Optional[list[str]] = None,
        status: int = 200,
        request_id: int = None
) -> None:
    """
    Sends data to groups in DCRF format. For use outside of consumers.

    DCRF format is:
        {
            "errors": [],
            "data": {},
            "action": 'action_name',
            "response_status": 200,
            "request_id": 1500000,
        }

    You need to have method in your consumer with name that you pass in this function in handler_name parameter.
    That method should serialize payload into JSON and send it to client.
    For example:

        async def data_to_groups(self, event):
            await self.send_json(event['payload'])


    Args:
        groups: list or tuple of group names
        handler_name: name of the function, that will receive data from group and send it via websocket to the client
        action: requested action from the client
        data: actual data to be sent
        errors: list of errors occurred while handling action
        status: HTTP response status code
        request_id: helps clients link messages they have sent to responses
    """

    channel_layer = get_channel_layer()

    await _reply_to_groups(
        groups=groups,
        handler_name=handler_name,
        channel_layer=channel_layer,
        action=action,
        data=data,
        errors=errors,
        status=status,
        request_id=request_id
    )


def is_attachment_file_size_valid(file):
    max_size = settings.MESSAGE_ATTACHMENT_MAX_SIZE
    max_size_mb = max_size // 1024 ** 2

    return file.size <= max_size, max_size_mb


def is_attachment_file_type_valid(file):
    return is_valid_file_type(settings.MESSAGE_ATTACHMENT_ALLOWED_MIME_TYPES, file)
