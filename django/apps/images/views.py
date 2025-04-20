from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Value, CharField
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from .models import ImageFolder, Slide


class ImageDatabaseView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "images/image_database.html"
    context_object_name = "items"
    permission_required = ["images.view_imagefolder", "images.view_slide"]

    def get_folder(self):
        folder_id = self.request.GET.get("folder")
        if not folder_id:
            return None
        return get_object_or_404(ImageFolder, id=folder_id)

    def get_queryset(self):
        current = self.get_folder()

        if not current:
            current = "root"
        children = (
            ImageFolder.objects.viewable(self.request.user, folder=current)
            .annotate(type=Value("folder", CharField()))
            .order_by("name")
        )
        slides = (
            Slide.objects.viewable(self.request.user, folder=current)
            .annotate(type=Value("slide", CharField()))
            .order_by("name")
        )

        return list(children) + list(slides)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current = self.get_folder()
        user = self.request.user

        context["current_folder"] = current
        context["breadcrumbs"] = self._generate_breadcrumbs(current)
        context["editable"] = current.is_owner(user) if current else user.is_admin()
        return context

    def _generate_breadcrumbs(self, folder):
        breadcrumbs = []
        current = folder

        while current:
            breadcrumbs.append({"id": current.id, "name": current.name})
            current = current.parent
        breadcrumbs.append({"id": "", "name": "Root"})

        breadcrumbs.reverse()
        return breadcrumbs
