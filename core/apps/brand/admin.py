from django.contrib import admin, messages
from django.utils import timezone
from django.utils.safestring import mark_safe

from core.apps.brand.forms import MatchAdminForm
from core.apps.brand.models import (
    Brand,
    Category,
    Format,
    Goal,
    Tag,
    Blog,
    Age,
    TargetAudience,
    Gender,
    GEO,
    ProductPhoto, GalleryPhoto, BusinessGroup, Match, Collaboration
)
from core.utils.admin import SearchByIdMixin


class ProductPhotoInline(admin.TabularInline):
    model = ProductPhoto


class GalleryPhotoInline(admin.TabularInline):
    model = GalleryPhoto


class BusinessGroupInline(admin.StackedInline):
    model = BusinessGroup


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
class BrandAdmin(SearchByIdMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'category', 'subs_count', 'avg_bill', 'city', 'offline_space')
    list_display_links = ('name',)
    filter_horizontal = ('tags', 'formats', 'goals', 'categories_of_interest',)
    raw_id_fields = ('user', 'city', 'target_audience')
    ordering = ('-id',)
    search_fields = ('name', 'user__email', 'user__phone')
    search_help_text = 'ID, name, user email or user phone'
    list_filter = ('category',)
    inlines = [BusinessGroupInline, ProductPhotoInline, GalleryPhotoInline]

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
    search_fields = ('blog', 'brand__name')
    search_help_text = 'Blog name, brand ID or brand name'
    raw_id_fields = ('brand',)

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


class GenderDistributedTARelatedModelAdmin(SearchByIdMixin, admin.ModelAdmin):
    """
    Base class for gender distributed related models of target audience

    Gender distributed model must have only two fields: "men" and "women".
    """
    list_display = ('id', 'men', 'women')
    list_display_links = ('id',)
    ordering = ('-id',)
    search_fields = ('id',)
    search_help_text = 'ID, men or women value'
    list_filter = (HasTargetAudienceFilter,)

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
            queryset |= self.model.objects.filter(men=search_term_as_int)
            queryset |= self.model.objects.filter(women=search_term_as_int)
        return queryset, may_have_duplicates


@admin.register(Age)
class AgeAdmin(GenderDistributedTARelatedModelAdmin):
    pass


@admin.register(Gender)
class GenderAdmin(GenderDistributedTARelatedModelAdmin):
    pass


@admin.register(GEO)
class GEOAdmin(SearchByIdMixin, admin.ModelAdmin):
    list_display = ('id', 'city', 'people_percentage', 'target_audience')
    list_display_links = ('city',)
    ordering = ('-id',)
    raw_id_fields = ('city', 'target_audience')
    search_fields = ('city__display_name',)
    search_help_text = 'ID, city name or people percentage'

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
            queryset |= self.model.objects.filter(people_percentage=search_term_as_int)
        return queryset, may_have_duplicates


class GEOInline(admin.TabularInline):
    model = GEO
    raw_id_fields = ('city',)


@admin.register(TargetAudience)
class TargetAudienceAdmin(SearchByIdMixin, admin.ModelAdmin):
    list_display = ('id', 'age', 'gender', 'income',)
    list_display_links = ('id',)
    ordering = ('-id',)
    inlines = [GEOInline]
    search_fields = ('id',)
    search_help_text = 'ID or income'
    raw_id_fields = ('age', 'gender')

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
            queryset |= self.model.objects.filter(income=search_term_as_int)
        return queryset, may_have_duplicates


class ImageBrandRelatedModelAdmin(SearchByIdMixin, admin.ModelAdmin):
    """
    Base ModelAdmin for brand related image model.

    Related model must have "image" field.
    """
    list_display = ['id', 'photo_image', 'brand']
    list_display_links = ('id',)
    ordering = ('-id',)
    raw_id_fields = ('brand',)
    search_fields = ('brand__name',)
    search_help_text = 'ID or brand name'
    list_per_page = 100

    @admin.display(description="Изображение")
    def photo_image(self, photo_instance):
        # Display image instead of path to image file
        return mark_safe(f'<img src={photo_instance.image.url} width=75>')


@admin.register(ProductPhoto)
class ProductPhotoAdmin(ImageBrandRelatedModelAdmin):
    list_filter = ('format',)

    def get_list_display(self, request):
        return [*self.list_display, 'format']


@admin.register(GalleryPhoto)
class GalleryPhotoAdmin(ImageBrandRelatedModelAdmin):
    pass


@admin.register(BusinessGroup)
class BusinessGroupAdmin(SearchByIdMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'brand')
    list_display_links = ('name',)
    ordering = ('-id',)
    search_fields = ('name', 'brand__name')
    search_help_text = 'ID, group name or brand name'
    raw_id_fields = ('brand',)
    list_per_page = 100


@admin.register(Match)
class MatchAdmin(SearchByIdMixin, admin.ModelAdmin):
    form = MatchAdminForm
    fields = ('initiator', 'target', 'is_match', 'room')
    list_display = ('id', 'initiator', 'target', 'is_match', 'like_at', 'match_at')
    list_display_links = ('id',)
    ordering = ('-id',)
    raw_id_fields = ('initiator', 'target', 'room')
    list_filter = ('is_match',)
    search_fields = ('initiator__name', 'target__name')
    search_help_text = 'ID, initiator name or target  name'

    def save_model(self, request, obj, form, change):
        # if adding a new instance, and it's a match, then manually set "match_at" to current time
        if not change:
            if obj.is_match:
                obj.match_at = timezone.now()
        # if changing an instance and "is_match" changed, then set it manually
        elif form.has_changed() and 'is_match' in form.changed_data:
            # if new value of "is_match" is True, then set it to current time
            if obj.is_match:
                obj.match_at = timezone.now()
            # if new value is False, then unset it
            else:
                obj.match_at = None

        super().save_model(request, obj, form, change)


@admin.register(Collaboration)
class CollaborationAdmin(SearchByIdMixin, admin.ModelAdmin):
    list_display = (
        'id', 'reporter', 'collab_with', 'match', 'created_at', 'new_offers', 'perception_change', 'difficulties'
    )

    list_display_links = ('id',)
    ordering = ('-created_at',)
    raw_id_fields = ('reporter', 'collab_with', 'match')
    list_filter = ('new_offers', 'perception_change', 'difficulties')
    search_fields = ('reporter__name', 'collab_with__name')
    search_help_text = 'ID, reporter name or "collab with" name'
    list_per_page = 100

    fieldsets = (
        (None, {'fields': ('reporter', 'collab_with', 'match')}),
        (
            'Overall success',
            {
                'classes': ['wide',],
                'fields': (
                    'success_assessment',
                    'success_reason',
                    'to_improve',
                )
            }
        ),
        (
            'Quantitative indicators',
            {
                'classes': ['wide', ],
                'fields': (
                    'subs_received',
                    'leads_received',
                    'sales_growth',
                    'audience_reach',
                    'bill_change',
                )
            }
        ),
        (
            'Partnership',
            {
                'classes': ['wide', ],
                'fields': (
                    'new_offers',
                    'new_offers_comment',
                )
            }
        ),
        (
            'Reputation',
            {
                'classes': ['wide', ],
                'fields': (
                    'perception_change',
                )
            }
        ),
        (
            'Compliance',
            {
                'classes': ['wide', ],
                'fields': (
                    'brand_compliance',
                )
            }
        ),
        (
            'platform interaction',
            {
                'classes': ['wide', ],
                'fields': (
                    'platform_help',
                    'difficulties',
                    'difficulties_comment',
                )
            }
        ),
    )
