from django.contrib import admin
from django.utils.translation import gettext as _, gettext_lazy as _lazy

from .models import ImageFolder, Slide, Tag


class RootFolderFilter(admin.SimpleListFilter):
    title = _lazy("Root Folder")
    parameter_name = "parent"

    def lookups(self, request, model_admin):
        return (
            (True, _("Root Folder")),
            (False, _("Non-Root Folder")),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(parent__isnull=self.value() == "True")
        return queryset


@admin.register(ImageFolder)
class FolderAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "parent",
        "author",
        "manager_group",
        "created_at",
        "updated_at",
    )
    search_fields = ("name",)
    ordering = ("-created_at",)
    readonly_fields = ("parent",)
    list_filter = (RootFolderFilter,)


@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "file",
        "folder",
        "author",
        "manager_group",
        "created_at",
        "updated_at",
    )
    search_fields = ("name", "information")
    ordering = ("-created_at",)
    readonly_fields = ("folder", "image_root", "metadata")
    prepopulated_fields = {"name": ("file",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("-created_at",)
