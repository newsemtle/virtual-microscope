import json
import os

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from apps.images.models import Slide
from .models import Annotation


class ImageViewerView(
    LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, TemplateView
):
    template_name = "viewer/viewer.html"
    permission_required = "images.view_slide"

    def test_func(self):
        slide_id = self.kwargs.get("slide_id")
        slide = get_object_or_404(Slide, id=slide_id)
        return slide.is_viewable_by(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slide_id = kwargs.get("slide_id")
        annotation_id = self.request.GET.get("annotation")

        slide = get_object_or_404(Slide, id=slide_id)
        annotation = None
        if annotation_id:
            annotation = get_object_or_404(Annotation, id=annotation_id)
            if annotation.slide != slide:
                annotation = None

        context["slide"] = slide
        context["slide"].file_name = os.path.basename(slide.file.name)
        context["slide"].created_at_formatted = timezone.localtime(
            slide.created_at
        ).strftime("%Y-%m-%d %H:%M:%S")
        context["slide"].updated_at_formatted = timezone.localtime(
            slide.updated_at
        ).strftime("%Y-%m-%d %H:%M:%S")

        if annotation:
            context["annotation"] = annotation
            context["annotation"].data = json.dumps(annotation.data)

        context["can_create_annotation"] = slide.is_viewable_by(
            self.request.user, include_lecture=False
        )
        context["can_edit_annotation"] = annotation and annotation.is_editable_by(
            self.request.user
        )
        return context
