from dateutil.relativedelta import relativedelta
from django.contrib import admin, messages
from django.utils import timezone

from core.apps.payments.forms import GiftPromoCodeAdminForm, SubscriptionAdminForm
from core.apps.payments.models import Tariff, PromoCode, GiftPromoCode, Subscription
from core.utils.admin import SearchByIdMixin


@admin.register(Tariff)
class TariffAdmin(SearchByIdMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'cost', 'duration')
    list_display_links = ('name',)
    search_fields = ('name',)
    search_help_text = 'ID, name or cost'
    ordering = ('-id',)
    list_per_page = 100

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        form.base_fields["duration"].help_text = (
            "Format: [days] [hours]:[minutes]:[seconds]. "
            "Example: 14 00:00:00 - 14 days"
        )

        return form

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
            queryset |= self.model.objects.filter(cost=search_term_as_int)
        return queryset, may_have_duplicates


@admin.register(PromoCode)
class PromoCodeAdmin(SearchByIdMixin, admin.ModelAdmin):
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
            queryset |= self.model.objects.filter(discount=search_term_as_int)
        return queryset, may_have_duplicates


@admin.register(GiftPromoCode)
class GiftPromoCodeAdmin(SearchByIdMixin, admin.ModelAdmin):
    form = GiftPromoCodeAdminForm
    fields = ('code', 'tariff', 'giver', 'expires_at', 'is_used', 'promocode')
    list_display = ('id', 'code', 'tariff', 'created_at', 'expires_at', 'is_used', 'giver')
    list_display_links = ('code',)
    readonly_fields = ('code',)
    search_fields = ('code', 'giver__name',)
    search_help_text = 'ID, code or giver name'
    ordering = ('-id',)
    raw_id_fields = ('giver', 'promocode',)
    list_per_page = 100


class SubscriptionGiftPromoCodeFilter(admin.SimpleListFilter):
    title = 'Gifted'
    parameter_name = 'gifted'

    def lookups(self, request, model_admin):
        return [
            ('1', 'Yes'),
            ('0', 'No')
        ]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset

        not_gifted = not bool(int(self.value()))

        return queryset.filter(gift_promocode__isnull=not_gifted)


@admin.register(Subscription)
class SubscriptionAdmin(SearchByIdMixin, admin.ModelAdmin):
    form = SubscriptionAdminForm
    list_display = ('id', 'brand', 'tariff', 'start_date', 'end_date', 'is_active', 'upgraded_from', 'upgraded_at')
    list_display_links = ('id',)
    list_filter = ('is_active', 'tariff', SubscriptionGiftPromoCodeFilter)
    raw_id_fields = ('brand', 'promocode', 'gift_promocode')
    ordering = ('-id',)
    search_fields = ('brand__name',)
    search_help_text = 'ID, brand ID or brand name'
    actions = ('deactivate',)

    fieldsets = (
        (None, {'fields': ('brand', 'tariff', 'is_active')}),
        ('Promo Codes', {'fields': ('promocode', 'gift_promocode')}),
        ('Upgrade Info', {'fields': ('upgraded_from', 'upgraded_at')})
    )

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
            queryset |= self.model.objects.filter(brand_id=search_term_as_int)
        return queryset, may_have_duplicates

    def save_model(self, request, obj, form, change):
        tariff_duration_days = obj.tariff.duration.days
        months = tariff_duration_days // 30
        days = tariff_duration_days % 30

        obj.end_date = timezone.now() + relativedelta(months=months, days=days)

        return super().save_model(request, obj, form, change)

    @admin.action(description='Deactivate selected subscriptions')
    def deactivate(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f'Deactivated {count} subscriptions!',
            messages.WARNING
        )
