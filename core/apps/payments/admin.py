from django.contrib import admin

from core.apps.payments.models import Tariff, PromoCode


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


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'discount', 'expires_at')
    list_display_links = ('code',)
    search_fields = ('code',)
    search_help_text = 'ID, code or discount'
    ordering = ('-id',)
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
            queryset |= self.model.objects.filter(id=search_term_as_int)
            queryset |= self.model.objects.filter(discount=search_term_as_int)
        return queryset, may_have_duplicates
