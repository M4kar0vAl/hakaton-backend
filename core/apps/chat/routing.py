from django.urls import re_path

from core.apps.chat.consumers import RoomConsumer, AdminRoomConsumer

urlpatterns = [
    re_path(r"ws/chat/$", RoomConsumer.as_asgi(), name='chat'),
    re_path(r"ws/admin-chat/$", AdminRoomConsumer.as_asgi(), name='admin_chat'),
]
