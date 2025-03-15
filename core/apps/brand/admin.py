from django.contrib import admin

from core.apps.brand.models import Brand


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
