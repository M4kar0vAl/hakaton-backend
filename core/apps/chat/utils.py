from typing import Any

from channels.layers import get_channel_layer


async def send_to_groups(data: dict[str, Any], groups: list[str] | tuple[str, ...]) -> None:
    """
    Отправляет данные указанным группам.

    Args:
        data: данные для отправки
        groups: список или кортеж с названиями групп, которым будут отправлены данные
    """
    if not isinstance(groups, (list, tuple)):
        raise TypeError('"groups" must be list or tuple')

    if not isinstance(data, dict):
        raise TypeError('"data" must be a dict')

    channel_layer = get_channel_layer()

    for group in groups:
        await channel_layer.group_send(group, data)
