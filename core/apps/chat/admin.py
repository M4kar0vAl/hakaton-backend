from django.contrib import admin

from core.apps.chat.forms import MessageAdminForm, RoomFavoritesAdminForm, MessageAttachmentAdminForm
from core.apps.chat.models import Room, Message, RoomFavorites, MessageAttachment
from core.utils.admin import SearchByIdMixin, custom_title_filter_factory


@admin.register(Room)
class RoomAdmin(SearchByIdMixin, admin.ModelAdmin):
    readonly_fields = ('id',)
    fields = ('id', 'type', 'participants')
    list_display = ('id', 'type')
    list_display_links = ('id',)
    list_filter = ('type',)
    filter_horizontal = ('participants',)
    ordering = ('-id',)
    search_fields = ('participants__email', 'participants__phone')
    search_help_text = 'ID, user email or user phone'


class MessageAttachmentInline(admin.TabularInline):
    model = MessageAttachment


message_room_type_filter = custom_title_filter_factory(admin.ChoicesFieldListFilter, 'Room type')


@admin.register(Message)
class MessageAdmin(SearchByIdMixin, admin.ModelAdmin):
    form = MessageAdminForm
    readonly_fields = ('id',)
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
    inlines = [MessageAttachmentInline]

    fieldsets = (
        (None, {'fields': ('id', 'user'), 'classes': ['wide',]}),
        ('Message', {'fields': ('text',), 'classes': ['wide',]}),
        ('Chat', {'fields': ('room',), 'classes': ['wide',]}),
    )

    @admin.display(description='Short text')
    def short_text(self, message):
        if len(message.text) > 20:
            return f'{message.text[:20]}...'

        return message.text


message_attachment_room_type_filter = custom_title_filter_factory(admin.ChoicesFieldListFilter, 'Room type')


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(SearchByIdMixin, admin.ModelAdmin):
    form = MessageAttachmentAdminForm
    readonly_fields = ('id',)
    fields = ('id', 'file', 'message')
    list_display = ('id', 'file', 'message', 'created_at')
    list_display_links = ('id',)
    list_filter = (
        ('message__room__type', message_attachment_room_type_filter),
    )
    raw_id_fields = ('message',)
    ordering = ('-created_at',)
    search_fields = ('message__text',)
    search_help_text = 'ID, message ID or message text'
    list_per_page = 100

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
            queryset |= self.model.objects.filter(message_id=search_term_as_int)
        return queryset, may_have_duplicates


room_favorites_room_type_filter = custom_title_filter_factory(admin.ChoicesFieldListFilter, 'Room type')


@admin.register(RoomFavorites)
class RoomFavoritesAdmin(SearchByIdMixin, admin.ModelAdmin):
    form = RoomFavoritesAdminForm
    fields = ('id', 'user', 'room')
    readonly_fields = ('id',)
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
