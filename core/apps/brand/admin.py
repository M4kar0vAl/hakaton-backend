from django.contrib import admin, messages

from core.apps.brand.models import Brand, Category, Format


class BaseBrandRelatedModelActionsMixin:
    """
    Mixin that provides actions for base related models for brand.

    Base related models must have "is_other" field.
    """
    actions = ('set_as_other', 'set_common')

    @admin.action(description='Set selected objects as other')
    def set_as_other(self, request, queryset):
        count = queryset.update(is_other=True)
        self.message_user(
            request,
            f'Set {count} objects as other. Nobody will be able to select them!',
            messages.WARNING
        )

    @admin.action(description='Set selected objects as common')
    def set_common(self, request, queryset):
        count = queryset.update(is_other=False)
        self.message_user(
            request,
            f'Set {count} objects as common. All users can see and select them now!',
            messages.WARNING
        )


class BaseBrandRelatedModelAdmin(BaseBrandRelatedModelActionsMixin, admin.ModelAdmin):
    """
    Base class for brand related models.

    Related model must have "name" and "is_other" fields.
    """
    list_display = ('id', 'name', 'is_other')
    list_display_links = ('name',)
    ordering = ('-name',)
    search_fields = ('name',)
    list_filter = ('is_other',)


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
                "classes": ["wide", ],
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
                "classes": ["wide", ],
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            kwargs['queryset'] = Category.objects.filter(is_other=False)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Category)
class CategoryAdmin(BaseBrandRelatedModelAdmin):
    pass


@admin.register(Format)
class FormatAdmin(BaseBrandRelatedModelAdmin):
    pass
