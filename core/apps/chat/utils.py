import inspect
from typing import Any, Optional

from channels.layers import get_channel_layer


async def reply_to_groups(
        groups: list[str] | tuple[str, ...],
        handler_name: str,
        action: str,
        data: dict[str, Any] = None,
        errors: Optional[list[str]] = None,
        status: int = 200,
        request_id: int = None
) -> None:
    """
    Sends data to groups in DCRF format.

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

    if not isinstance(groups, (list, tuple)):
        raise TypeError("'groups' must be list or tuple")

    if not isinstance(data, dict):
        raise TypeError("'data' must be a dict")

    if errors is None:
        errors = []

    payload = {
        "errors": errors,
        "data": data,
        "action": action,
        "response_status": status,
        "request_id": request_id,
    }

    channel_layer = get_channel_layer()

    for group in groups:
        await channel_layer.group_send(group, {'type': handler_name, 'payload': payload})


def get_method_name():
    """
    Get name of function where it was called.
    It might be useful to get action name in consumer's method.

    If you want to change the method's name you will not need to change the code where it is used.
    """
    return inspect.stack()[1][3]
