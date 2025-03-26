from django.contrib import admin

from core.apps.blacklist.admin import custom_title_filter_factory
from core.apps.chat.models import Room, Message, RoomFavorites
from core.utils.admin import SearchByIdMixin


@admin.register(Room)
class RoomAdmin(SearchByIdMixin, admin.ModelAdmin):
    list_display = ('id', 'type')
    list_display_links = ('id',)
    list_filter = ('type',)
    filter_horizontal = ('participants',)
    ordering = ('-id',)
    search_fields = ('participants__email', 'participants__phone')
    search_help_text = 'ID, user email or user phone'


message_room_type_filter = custom_title_filter_factory(admin.ChoicesFieldListFilter, 'Room type')


@admin.register(Message)
class MessageAdmin(SearchByIdMixin, admin.ModelAdmin):
    list_display = ('id', 'short_text', 'user', 'created_at', 'room')
    list_display_links = ('short_text',)
    list_filter = (
        ('room__type', message_room_type_filter),
    )
    search_fields = ('text',)
    search_help_text = 'ID or text'
    raw_id_fields = ('user', 'room')
    ordering = ('-created_at',)
    list_per_page = 100

    @admin.display(description='Short text')
    def short_text(self, message):
        if len(message.text) > 20:
            return f'{message.text[:20]}...'

        return message.text


room_favorites_room_type_filter = custom_title_filter_factory(admin.ChoicesFieldListFilter, 'Room type')


@admin.register(RoomFavorites)
class RoomFavoritesAdmin(SearchByIdMixin, admin.ModelAdmin):
    list_display = ('id', 'user', 'room')
    list_display_links = ('id',)
    list_filter = (
        ('room__type', room_favorites_room_type_filter),
    )
    raw_id_fields = ('user', 'room')
    search_fields = ('user__email', 'user__phone')
    search_help_text = 'ID, user email or user phone'
    ordering = ('-id',)
    list_per_page = 100
