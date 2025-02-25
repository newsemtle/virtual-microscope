from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .forms import UserChangeForm, UserCreationForm
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
        types = GroupProfile.TypeChoices.choices
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


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ("username", "first_name", "last_name", "is_staff")
    list_filter = ("groups",)
    fieldsets = [
        (
            None,
            {"fields": ("username", "password")},
        ),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "email")},
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
