from django.contrib import admin

from .models import Lecture, LectureContent, LectureFolder


@admin.register(LectureFolder)
class LectureFolderAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "created_at", "updated_at", "author")
    search_fields = ("name",)
    ordering = ("-created_at",)
    readonly_fields = ("parent",)


class LectureContentInline(admin.StackedInline):
    model = LectureContent
    extra = 0
    fields = ("order", "slide", "annotation")
    readonly_fields = ("order", "slide", "annotation")
    ordering = ("order",)
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ("name", "author", "created_at", "updated_at", "is_open")
    list_filter = ("author", "is_open")
    search_fields = ("name", "author__username")
    ordering = ("-updated_at",)
    filter_horizontal = ("viewer_groups",)
    readonly_fields = ("folder",)

    inlines = [LectureContentInline]
