from django.contrib import admin

from .models import (
    Folder,
    Slide,
    Tag,
)


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "created_at", "updated_at", "author")
    search_fields = ("name",)
    ordering = ("-created_at",)
    readonly_fields = ("parent",)


@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ("name", "file", "folder", "created_at", "updated_at", "author")
    search_fields = ("name", "information")
    ordering = ("-created_at",)
    readonly_fields = ("folder", "image_root", "metadata")
    prepopulated_fields = {"name": ("file",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("-created_at",)
