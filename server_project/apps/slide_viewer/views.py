import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from apps.database.models import Slide
from apps.slide_viewer.models import Annotation

logger = logging.getLogger("django")


class SlideView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Render a page with the OpenSeadragon viewer for the specified slide."""

    template_name = "slide_viewer/viewer.html"
    permission_required = "database.view_slide"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slide_id = kwargs.get("slide_id")
        annotation_id = self.request.GET.get("annotation")

        slide = get_object_or_404(Slide, id=slide_id)
        try:
            annotation = Annotation.objects.get(id=annotation_id)
            if annotation.slide != slide:
                raise Annotation.DoesNotExist
        except Annotation.DoesNotExist or AttributeError:
            annotation = None

        logger.info(f"SlideView: {slide} - {annotation}")

        context["slide"] = slide
        context["annotation"] = annotation
        context["editable"] = slide.user_can_edit(self.request.user)
        return context


def save_annotation(request, slide_id):
    """Save an annotation for a slide."""

    slide = get_object_or_404(Slide, id=slide_id)

    if request.method == "POST":
        annotation_id = request.POST.get("annotationId")
        name = request.POST.get("name")
        description = request.POST.get("description")
        data = json.loads(request.POST.get("data", "[]"))

        if annotation_id:
            try:
                annotation = Annotation.objects.get(id=annotation_id)
                if annotation.user_can_edit(request.user):
                    annotation.name = name
                    annotation.description = description
                    annotation.data = data
                    annotation.save()
                    return HttpResponse(f'Annotation "{name}" updated successfully.')
                else:
                    return HttpResponse("You are not allowed to edit this annotation.")
            except Annotation.DoesNotExist or AttributeError:
                return HttpResponse("Annotation not found.")
        else:
            Annotation.objects.create(
                name=name,
                description=description,
                data=data,
                author=request.user,
                slide=slide,
            )
            return HttpResponse(f'Annotation "{name}" created successfully.')
