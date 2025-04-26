from django.contrib import admin

from core.apps.blacklist.forms import BlackListAdminForm
from core.apps.blacklist.models import BlackList
from core.common.admin import SearchByIdMixin, custom_title_filter_factory

initiator_category_filter = custom_title_filter_factory(admin.RelatedFieldListFilter, 'Initiator category')
blocked_category_filter = custom_title_filter_factory(admin.RelatedFieldListFilter, 'Blocked category')


@admin.register(BlackList)
class BlacklistAdmin(SearchByIdMixin, admin.ModelAdmin):
    form = BlackListAdminForm
    fields = ('id', 'initiator', 'blocked')
    readonly_fields = ('id',)
    list_display = ('id', 'initiator', 'blocked')
    list_display_links = ('id',)
    raw_id_fields = ('initiator', 'blocked')
    ordering = ('-id',)
    search_fields = ('initiator__name', 'blocked__name')
    search_help_text = 'ID, initiator name or blocked name'
    list_filter = (
        ('initiator__category', initiator_category_filter),
        ('blocked__category', blocked_category_filter),
    )
    list_per_page = 100
