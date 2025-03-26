from django.contrib import admin

from core.apps.blacklist.forms import BlackListAdminForm
from core.apps.blacklist.models import BlackList
from core.utils.admin import SearchByIdMixin


def custom_title_filter_factory(filter_cls, title):
    """
    Factory that creates filters with default logic and custom title.

    Use this if you need default filter but with overridden title
    (e.g. if you have several fields that point to the same model, and you need to filter that related model field)

    Example:
        class Category(models.Model):
            ...

            class Meta:
                verbose_name = 'Категория'

        class Brand(models.Model):
            category = models.ForeignKey(Category)
            ...

        class Blacklist(models.Model):
            initiator = models.ForeignKey(Brand)
            blocked = models.ForeignKey(Brand)

    If default filters are specified using list_filter = ('initiator__category', 'blocked__category'), then
    their title will be the same i.e. Category model's verbose_name attribute.

    To differentiate those filters, you can use this factory and specify title to use for each filter.

    Usage:
        initiator_category_filter = custom_title_filter_factory(admin.RelatedFieldListFilter, 'Initiator category')
        blocked_category_filter = custom_title_filter_factory(admin.RelatedFieldListFilter, 'Blocked category')

        Then in ModelAdmin:
            list_filter = (
                ('initiator__category', initiator_category_filter),
                ('blocked__category', blocked_category_filter)
            )
    """

    class Wrapper(filter_cls):
        def __new__(cls, *args, **kwargs):
            instance = filter_cls(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper


initiator_category_filter = custom_title_filter_factory(admin.RelatedFieldListFilter, 'Initiator category')
blocked_category_filter = custom_title_filter_factory(admin.RelatedFieldListFilter, 'Blocked category')


@admin.register(BlackList)
class BlacklistAdmin(SearchByIdMixin, admin.ModelAdmin):
    form = BlackListAdminForm
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
