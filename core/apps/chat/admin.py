from django.contrib import admin

from core.apps.blacklist.admin import custom_title_filter_factory
from core.apps.chat.models import Room, Message, RoomFavorites


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'type')
    list_display_links = ('id',)
    list_filter = ('type',)
    filter_horizontal = ('participants',)
    ordering = ('-id',)


message_room_type_filter = custom_title_filter_factory(admin.ChoicesFieldListFilter, 'Room type')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
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

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )
        try:
            search_term_as_int = int(search_term)
        except ValueError:
            pass
        else:
            queryset |= self.model.objects.filter(id=search_term_as_int)
        return queryset, may_have_duplicates


room_favorites_room_type_filter = custom_title_filter_factory(admin.ChoicesFieldListFilter, 'Room type')


@admin.register(RoomFavorites)
class RoomFavoritesAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'room')
    list_display_links = ('id',)
    list_filter = (
        ('room__type', room_favorites_room_type_filter),
    )
    raw_id_fields = ('user', 'room')
    ordering = ('-id',)
    list_per_page = 100
