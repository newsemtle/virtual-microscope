import json

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from apps.database.models import Slide
from .models import Annotation


class SlideView(
    LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, TemplateView
):
    template_name = "slide_viewer/viewer.html"
    permission_required = "database.view_slide"

    def test_func(self):
        slide_id = self.kwargs.get("slide_id")
        slide = get_object_or_404(Slide, id=slide_id)
        return slide.user_can_view(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slide_id = kwargs.get("slide_id")
        annotation_id = self.request.GET.get("annotation")

        slide = get_object_or_404(Slide, id=slide_id)
        try:
            annotation = Annotation.objects.get(id=annotation_id)
            if annotation.slide != slide:
                raise Annotation.DoesNotExist
        except Annotation.DoesNotExist:
            annotation = None
        except ValueError:
            annotation = None

        context["slide"] = slide
        if annotation:
            context["annotation"] = annotation
            context["annotation"].data = json.dumps(annotation.data)

        context["can_create_annotation"] = slide.user_can_view(self.request.user)
        context["can_edit_annotation"] = (
            annotation.user_can_edit(self.request.user) if annotation else False
        )
        return context
