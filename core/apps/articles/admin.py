from django.contrib import admin, messages

from core.apps.articles.models import Article, Tutorial
from core.common.admin import SearchByIdMixin

admin.site.register(Article)


@admin.register(Tutorial)
class TutorialAdmin(SearchByIdMixin, admin.ModelAdmin):
    readonly_fields = ['id']
    list_display = ['id', 'title', 'excerpt', 'is_published']
    list_display_links = ['title']
    search_fields = ['title', 'excerpt']
    search_help_text = 'ID, title or excerpt'
    list_filter = ['is_published']
    list_per_page = 100
    actions = ['publish', 'unpublish']

    fieldsets = [
        (None, {'fields': ('id', 'is_published'), 'classes': ['wide', ]}),
        ('Preview', {'fields': ('title', 'excerpt', 'preview_video'), 'classes': ['wide', ]}),
        ('Content', {'fields': ('body',), 'classes': ['wide', ]}),
    ]

    @admin.action(description='Publish selected tutorials')
    def publish(self, request, queryset):
        count = queryset.update(is_published=True)
        self.message_user(
            request,
            f'Published {count} objects. Now users can see them!',
            messages.WARNING
        )

    @admin.action(description='Unpublish selected tutorials')
    def unpublish(self, request, queryset):
        count = queryset.update(is_published=False)
        self.message_user(
            request,
            f'Unpublished {count} objects. Now users cannot see them!',
            messages.WARNING
        )
