from django.urls import path
from rest_framework import routers

from core.apps.chat.api import RoomFavoritesViewSet, MessageAttachmentCreateView

router = routers.DefaultRouter()
router.register('chat_favorites', RoomFavoritesViewSet, basename='chat_favorites')

urlpatterns = [
    path('message_attachments/', MessageAttachmentCreateView.as_view(), name='message_attachments')
]

urlpatterns += router.urls
