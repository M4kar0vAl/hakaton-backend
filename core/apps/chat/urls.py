from rest_framework import routers

from core.apps.chat.api import RoomFavoritesViewSet

router = routers.DefaultRouter()
router.register('chat_favorites', RoomFavoritesViewSet, basename='chat_favorites')

urlpatterns = []

urlpatterns += router.urls
