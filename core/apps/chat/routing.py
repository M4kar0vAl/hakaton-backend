from django.urls import re_path

from core.apps.chat.consumers import RoomConsumer, AdminRoomConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/$", RoomConsumer.as_asgi()),
    re_path(r"ws/admin-chat/$", AdminRoomConsumer.as_asgi()),
]
