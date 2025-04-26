class SearchByIdMixin:
    """
    Mixin for ModelAdmin classes, that enables integer search by id.

    You must specify some other fields in search_fields, for the search bar to appear in the admin panel.
    """

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
