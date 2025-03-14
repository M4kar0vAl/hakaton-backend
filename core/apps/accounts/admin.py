from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from core.apps.accounts.forms import UserChangeForm, UserCreateForm

User = get_user_model()


class UserAdminActionsMixin:
    actions = ('activate_users', 'deactivate_users')

    @admin.action(description='Activate selected users')
    def activate_users(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'Activated {count} users')

    @admin.action(description='Deactivate selected users')
    def deactivate_users(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {count} users', messages.WARNING)


@admin.register(User)
class UserAdmin(UserAdminActionsMixin, BaseUserAdmin):
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("fullname", "phone")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")})
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
        (
            "Personal info",
            {
                "classes": ("wide",),
                "fields": ("fullname", "phone")
            }
        ),
        (
            "Permissions",
            {
                "classes": ("wide",),
                "fields": ("is_active", "is_staff", "is_superuser")
            }
        ),
    )
    form = UserChangeForm
    add_form = UserCreateForm
    list_display = ("id", "fullname", "email", "phone", "is_active", "is_staff", "is_superuser", "last_login", "date_joined")
    list_display_links = ("fullname",)
    list_filter = ("is_staff", "is_superuser", "is_active")
    list_per_page = 100
    search_fields = ("email", "phone", "fullname")
    readonly_fields = ("date_joined", "last_login")
    ordering = ("id",)

    def get_readonly_fields(self, request, obj=None):
        # if current user is not a superuser
        if not request.user.is_superuser:
            # if adding a new user, disable "is_superuser" field
            if not obj:
                return [*self.readonly_fields, 'is_superuser']

            # if changing user, disable permissions, groups and "is_superuser" field
            if obj:
                return [*self.readonly_fields, 'user_permissions', 'groups', 'is_superuser']

        return super().get_readonly_fields(request, obj)

    def has_change_permission(self, request, obj=None):
        if not obj:
            return True

        # superusers can change everyone, even other superusers
        if obj.is_superuser:
            return request.user.is_superuser

        # staff users can be changed only by themselves and superusers
        if obj.is_staff:
            return request.user == obj or request.user.is_superuser

        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not obj:
            return True

        # if current user is not a superuser
        if not request.user.is_superuser:
            # if deleting object is staff user or superuser, then deny permission
            if obj.is_staff or obj.is_superuser:
                return False

        # otherwise check if user has general permission to delete users
        return super().has_delete_permission(request, obj)
