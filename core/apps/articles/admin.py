from django.contrib import admin, messages

from core.apps.articles.models import (
    Article,
    Tutorial,
    CommunityArticle,
    MediaArticle,
    NewsArticle
)
from core.common.admin import SearchByIdMixin

admin.site.register(Article)


class BaseArticleAdmin(SearchByIdMixin, admin.ModelAdmin):
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
        ('Preview', {'fields': ('title', 'excerpt', 'preview'), 'classes': ['wide', ]}),
        ('Content', {'fields': ('body',), 'classes': ['wide', ]}),
    ]

    @admin.action(description='Publish selected articles')
    def publish(self, request, queryset):
        count = queryset.update(is_published=True)
        self.message_user(
            request,
            f'Published {count} objects. Now users can see them!',
            messages.WARNING
        )

    @admin.action(description='Unpublish selected articles')
    def unpublish(self, request, queryset):
        count = queryset.update(is_published=False)
        self.message_user(
            request,
            f'Unpublished {count} objects. Now users cannot see them!',
            messages.WARNING
        )


@admin.register(Tutorial)
class TutorialAdmin(BaseArticleAdmin):
    pass


@admin.register(CommunityArticle)
class CommunityArticleAdmin(BaseArticleAdmin):
    pass


@admin.register(MediaArticle)
class MediaArticleAdmin(BaseArticleAdmin):
    pass


@admin.register(NewsArticle)
class NewsArticleAdmin(BaseArticleAdmin):
    pass
