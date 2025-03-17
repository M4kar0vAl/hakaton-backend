from django.contrib import admin, messages

from core.apps.brand.models import Brand, Category, Format, Goal, Tag, Blog, Age, TargetAudience, Gender, GEO


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

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'tags':
            kwargs['queryset'] = Tag.objects.filter(is_other=False)
        elif db_field.name == 'goals':
            kwargs['queryset'] = Goal.objects.filter(is_other=False)
        elif db_field.name == 'formats':
            kwargs['queryset'] = Format.objects.filter(is_other=False)
        elif db_field.name == 'categories_of_interest':
            kwargs['queryset'] = Category.objects.filter(is_other=False)

        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(Category)
class CategoryAdmin(BaseBrandRelatedModelAdmin):
    pass


@admin.register(Format)
class FormatAdmin(BaseBrandRelatedModelAdmin):
    pass


@admin.register(Goal)
class GoalAdmin(BaseBrandRelatedModelAdmin):
    pass


@admin.register(Tag)
class TagAdmin(BaseBrandRelatedModelAdmin):
    pass


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('id', 'blog', 'brand')
    list_display_links = ('blog',)
    ordering = ('-id',)
    search_fields = ('blog', 'brand__id', 'brand__name')
    raw_id_fields = ('brand',)


class HasTargetAudienceFilter(admin.SimpleListFilter):
    title = 'Has associated target audience'
    parameter_name = 'has_target_audience'

    def lookups(self, request, model_admin):
        return [
            ('1', 'Yes'),
            ('0', 'No')
        ]

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(target_audience__isnull=False)
        elif self.value() == '0':
            return queryset.filter(target_audience__isnull=True)

        return queryset


class GenderDistributedTARelatedModelAdmin(admin.ModelAdmin):
    """
    Base class for gender distributed related models of target audience

    Gender distributed model must have only two fields: "men" and "women".
    """
    list_display = ('id', 'men', 'women')
    list_display_links = ('id',)
    ordering = ('-id',)
    search_fields = ('id', 'men', 'women')
    list_filter = (HasTargetAudienceFilter,)


@admin.register(Age)
class AgeAdmin(GenderDistributedTARelatedModelAdmin):
    pass


@admin.register(Gender)
class GenderAdmin(GenderDistributedTARelatedModelAdmin):
    pass


@admin.register(GEO)
class GEOAdmin(admin.ModelAdmin):
    list_display = ('id', 'city', 'people_percentage', 'target_audience')
    list_display_links = ('city',)
    ordering = ('-id',)
    raw_id_fields = ('city', 'target_audience')
    search_fields = ('id', 'city__display_name', 'people_percentage')


class GEOInline(admin.TabularInline):
    model = GEO
    raw_id_fields = ('city',)


@admin.register(TargetAudience)
class TargetAudienceAdmin(admin.ModelAdmin):
    list_display = ('id', 'age', 'gender', 'income',)
    list_display_links = ('id',)
    ordering = ('-id',)
    inlines = [GEOInline]
    search_fields = ('id', 'income')
