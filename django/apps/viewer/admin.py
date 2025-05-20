from django.contrib import admin

from .models import Annotation


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ("name", "slide", "created_at", "updated_at")
    list_filter = ("slide",)
    search_fields = ("name", "description")
    ordering = ("-created_at",)
    readonly_fields = ("slide", "data")
