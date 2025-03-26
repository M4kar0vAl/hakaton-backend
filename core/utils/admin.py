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
