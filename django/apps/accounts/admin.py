from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from import_export import resources
from import_export.admin import ImportExportMixin

from .forms import AdminUserChangeForm, AdminUserCreationForm, AdminPasswordChangeForm
from .models import User, GroupProfile

admin.site.unregister(Group)


class GroupProfileInline(admin.StackedInline):
    model = GroupProfile
    can_delete = False
    extra = 1
    min_num = 1
    readonly_fields = ("base_folder",)
    verbose_name = "Profile"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("type",) + self.readonly_fields
        return self.readonly_fields


class GroupTypeFilter(admin.SimpleListFilter):
    title = "Type"
    parameter_name = "type"

    def lookups(self, request, model_admin):
        types = GroupProfile.Type.choices
        return [(value, display) for value, display in types]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(profile__type=self.value())
        return queryset


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "get_type")
    list_filter = (GroupTypeFilter,)
    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("permissions",)

    inlines = [GroupProfileInline]

    def get_type(self, obj):
        return obj.profile.get_type_display()

    get_type.short_description = "Type"


class UserResource(resources.ModelResource):
    class Meta:
        model = User

    def before_import(self, dataset, **kwargs):
        required_columns = ["username", "password", "first_name", "last_name"]

        missing_columns = [
            col for col in required_columns if col not in dataset.headers
        ]
        if missing_columns:
            raise ValidationError(
                f"Missing required columns: {', '.join(missing_columns)}"
            )

        super().before_import(dataset, **kwargs)

    def before_import_row(self, row, **kwargs):
        required_columns = ["username", "password", "first_name", "last_name"]

        for col in required_columns:
            if not row.get(col):
                raise ValidationError(f"{col} is required")

        super().before_import_row(row, **kwargs)

    def save_instance(self, instance, is_create, row, **kwargs):
        raw_password = instance.password

        # Only hash if it’s not already hashed
        if raw_password and not raw_password.startswith("pbkdf2_"):
            instance.set_password(raw_password)

        return super().save_instance(instance, is_create, row, **kwargs)


@admin.register(User)
class UserAdmin(ImportExportMixin, BaseUserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    change_password_form = AdminPasswordChangeForm
    resource_class = UserResource

    list_display = ("username", "first_name", "last_name", "is_staff")
    list_filter = ("groups",)
    fieldsets = [
        (
            None,
            {"fields": ("username", "password")},
        ),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "email", "profile_image")},
        ),
        (
            "Permissions",
            {
                "fields": ("groups", "base_lecture_folder"),
            },
        ),
        (
            "Advanced Settings",
            {"fields": ("is_active", "is_staff", "is_superuser")},
        ),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "profile_image",
                    "password1",
                    "password2",
                    "groups",
                ),
            },
        ),
    ]
    search_fields = ["username"]
    ordering = ["username"]
    filter_horizontal = ("groups",)
    readonly_fields = ("base_lecture_folder",)

    def generate_log_entries(self, result, request):
        pass
