from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.hashers import identify_hasher
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _, gettext_lazy as _lazy
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
    readonly_fields = ("base_image_folder",)
    verbose_name = _lazy("Profile")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("type",) + self.readonly_fields
        return self.readonly_fields


class GroupTypeFilter(admin.SimpleListFilter):
    title = _lazy("Type")
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
    fieldsets = [(None, {"fields": ("name",)})]

    inlines = [GroupProfileInline]

    def get_type(self, obj):
        return obj.profile.get_type_display()

    get_type.short_description = _lazy("Type")


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        import_id_fields = ("username",)
        skip_unchanged = True
        report_skipped = True

    def before_import(self, dataset, **kwargs):
        required_columns = ["username", "password", "first_name", "last_name"]

        missing_columns = [
            col for col in required_columns if col not in dataset.headers
        ]
        if missing_columns:
            # 사용자(admin)에게 전달되는 에러메시지
            raise ValidationError(
                _("Missing required columns: {columns}").format(
                    columns=", ".join(missing_columns)
                )
            )

        super().before_import(dataset, **kwargs)

    def before_import_row(self, row, **kwargs):
        required_columns = ["username", "password", "first_name", "last_name"]

        for col in required_columns:
            if not row.get(col):
                # 사용자(admin)에게 전달되는 에러메시지
                raise ValidationError(_("{column} is required").format(column=col))

        super().before_import_row(row, **kwargs)

    def save_instance(self, instance, is_create, row, **kwargs):
        raw_password = instance.password

        try:
            identify_hasher(raw_password)
        except ValueError:
            # hash password
            instance.set_password(raw_password)

        return super().save_instance(instance, is_create, row, **kwargs)

    def get_export_fields(self, selected_fields=None):
        return [
            field
            for field in super().get_export_fields(selected_fields)
            if field.column_name != "password"
        ]


@admin.register(User)
class UserAdmin(ImportExportMixin, BaseUserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    change_password_form = AdminPasswordChangeForm
    resource_class = UserResource

    list_display = ("username", "get_full_name", "email", "get_type", "is_staff")
    list_filter = ("groups",)
    fieldsets = [
        (
            None,
            {"fields": ("username", "password")},
        ),
        (
            _lazy("Information"),
            {"fields": ("first_name", "last_name", "email", "profile_image")},
        ),
        (
            _lazy("Permissions"),
            {"fields": ("groups", "base_lecture_folder")},
        ),
        (
            _lazy("Advanced Settings"),
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
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "email",
                    "groups",
                ),
            },
        ),
    ]
    search_fields = ["username"]
    ordering = ["username"]
    filter_horizontal = ("groups",)
    readonly_fields = ("base_lecture_folder",)

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_type(self, obj):
        if obj.is_admin():
            return "Admin"
        elif obj.is_publisher():
            return "Publisher"
        elif obj.is_viewer():
            return "Viewer"
        else:
            return None

    get_full_name.short_description = _lazy("Name")
    get_type.short_description = _lazy("Type")

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        else:
            if obj.is_admin():
                return [
                    (name, data)
                    for name, data in self.fieldsets
                    if name != _("Permissions")
                ]
            return self.fieldsets

    def generate_log_entries(self, result, request):
        # suppress error
        pass
