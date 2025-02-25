from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from .models import Folder, Slide


class DatabaseView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "database/database.html"
    context_object_name = "items"
    permission_required = ["database.view_folder", "database.view_slide"]

    def get_folder(self):
        folder_id = self.request.GET.get("folder")
        if not folder_id:
            return None
        return get_object_or_404(Folder, id=folder_id)

    def get_queryset(self):
        current = self.get_folder()

        if current:
            subfolders = current.subfolders.all()
        else:
            subfolders = Folder.objects.base_folders()

        slides = Slide.objects.viewable_by_folder(self.request.user, current)

        for folder in subfolders:
            folder.type = "folder"

        for slide in slides:
            slide.type = "slide"

        items = list(subfolders) + list(slides)
        return sorted(items, key=lambda x: (x.type, x.name.lower()))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current = self.get_folder()

        context["current_folder"] = current
        context["breadcrumbs"] = self._generate_breadcrumbs(current)
        context["editable"] = (
            current.user_can_edit(self.request.user)
            if current
            else self.request.user.is_admin()
        )
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
