from django.contrib import admin

from core.apps.chat.models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'type')
    list_display_links = ('id',)
    list_filter = ('type',)
    filter_horizontal = ('participants',)
    ordering = ('-id',)
