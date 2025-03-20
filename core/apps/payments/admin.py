from django.contrib import admin

from core.apps.payments.models import Tariff


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'cost', 'duration')
    list_display_links = ('name',)
    search_fields = ('id', 'name', 'cost')
    ordering = ('-id',)
    list_per_page = 100
    search_help_text = 'ID, name or cost'

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        form.base_fields["duration"].help_text = (
            "Format: [days] [hours]:[minutes]:[seconds]. "
            "Example: 14 00:00:00 - 14 days"
        )

        return form
