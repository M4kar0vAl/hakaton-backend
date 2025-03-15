from django.contrib import admin, messages

from core.apps.brand.models import Brand, Category


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'category', 'subs_count', 'avg_bill', 'city', 'offline_space')
    list_display_links = ('name',)
    filter_horizontal = ('tags', 'formats', 'goals', 'categories_of_interest',)
    raw_id_fields = ('user', 'city',)
    ordering = ('-id',)
    search_fields = ('name', 'user__email', 'user__phone')
    list_filter = ('category',)

    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            "Questionnaire Part 1",
            {
                "classes": ["wide",],
                "fields": (
                    ("name", "position"),
                    "tg_nickname",
                    "city",
                    "category",
                    ("subs_count", "avg_bill"),
                    ("inst_url", "vk_url", "tg_url"),
                    ("wb_url", "lamoda_url", "site_url"),
                    "tags",
                    "uniqueness",
                    ("logo", "photo"),
                )
            }
        ),
        (
            "Questionnaire Part 2",
            {
                "classes": ["wide",],
                "fields": (
                    "mission_statement",
                    "offline_space",
                    "problem_solving",
                    "target_audience",
                    "formats",
                    "goals",
                    "categories_of_interest",
                ),
            },
        ),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_other')
    list_display_links = ('name',)
    ordering = ('-name',)
    search_fields = ('name',)
    list_filter = ('is_other',)
    actions = ('set_as_other', 'set_common')

    @admin.action(description='Set selected categories as other')
    def set_as_other(self, request, queryset):
        count = queryset.update(is_other=True)
        self.message_user(
            request,
            f'Set {count} categories as other. Nobody will be able to select them!',
            messages.WARNING
        )

    @admin.action(description='Set selected categories as common')
    def set_common(self, request, queryset):
        count = queryset.update(is_other=False)
        self.message_user(
            request,
            f'Set {count} categories as common. All users can see and select them now!',
            messages.WARNING
        )
