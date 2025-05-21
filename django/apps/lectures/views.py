import json

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
    PermissionRequiredMixin,
)
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import CharField, Value
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import ListView, TemplateView

from apps.accounts.models import GroupProfile
from apps.images.models import Slide, ImageFolder
from apps.lectures.models import Lecture, LectureFolder


class LectureBulletinsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "lectures/lecture_bulletins.html"
    context_object_name = "lectures"
    permission_required = "lectures.view_lecture"

    def get_queryset(self):
        user = self.request.user
        lectures = (
            Lecture.objects.viewable(user).filter(is_open=True).order_by("-updated_at")
        )
        return lectures

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for lecture in context["lectures"]:
            lecture.is_editable_by = lecture.is_editable_by(self.request.user)
        return context


class LectureDatabaseView(
    LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, ListView
):
    template_name = "lectures/lecture_database.html"
    context_object_name = "items"
    permission_required = ["lectures.view_lecturefolder", "lectures.view_lecture"]

    def get_folder(self):
        folder_id = self.request.GET.get("folder")
        if not folder_id:
            return None  # Root
        return get_object_or_404(LectureFolder, id=folder_id)

    def test_func(self):
        user = self.request.user
        current = self.get_folder()
        if current:
            return current.is_viewable_by(user)
        return user.is_admin()

    def handle_no_permission(self):
        user = self.request.user
        if not user.is_authenticated:
            return super().handle_no_permission()

        folder = user.base_lecture_folder
        if folder:
            return redirect(
                reverse_lazy("lectures:lecture-database") + f"?folder={folder.id}"
            )
        else:
            raise PermissionDenied(_("You don't have permission to access this page."))

    def get_queryset(self):
        user = self.request.user
        current = self.get_folder()

        if not current:
            current = "root"
        children = (
            LectureFolder.objects.viewable(user, parent=current)
            .annotate(type=Value("folder", CharField()))
            .order_by("name")
        )
        lectures = (
            Lecture.objects.viewable(user, folder=current)
            .annotate(type=Value("lecture", CharField()))
            .order_by("name")
        )

        for child in children:
            child.file_count = child.file_count(cumulative=True)

        return list(children) + list(lectures)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current = self.get_folder()
        context["current_folder"] = current
        context["breadcrumbs"] = self._generate_breadcrumbs(current)

        if current:
            context["parent_available"] = (
                True if current.parent else self.request.user.is_admin()
            )
        else:
            context["parent_available"] = False

        return context

    def _generate_breadcrumbs(self, folder):
        breadcrumbs = []
        current = folder

        while current:
            breadcrumbs.append({"id": current.id, "name": current.name})
            current = current.parent
        if self.request.user.is_admin():
            breadcrumbs.append({"id": "", "name": _("Root")})

        breadcrumbs.reverse()
        return breadcrumbs


class LectureView(
    LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, ListView
):
    template_name = "lectures/lecture_view.html"
    context_object_name = "contents"
    permission_required = "lectures.view_lecture"

    def get_lecture(self):
        lecture_id = self.kwargs.get("lecture_id")
        return Lecture.objects.get(id=lecture_id)

    def test_func(self):
        lecture = self.get_lecture()
        return lecture.is_viewable_by(self.request.user)

    def get_queryset(self):
        contents = self.get_lecture().contents.all().order_by("order")
        return contents

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lecture"] = self.get_lecture()
        context["is_editable"] = self.get_lecture().is_editable_by(self.request.user)
        return context


class LectureEditView(
    LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, TemplateView
):
    template_name = "lectures/lecture_edit.html"
    permission_required = ["lectures.change_lecture", "images.view_slide"]

    def get_lecture(self):
        lecture_id = self.kwargs.get("lecture_id")
        return Lecture.objects.get(id=lecture_id)

    def test_func(self):
        lecture = self.get_lecture()
        return lecture.is_editable_by(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lecture"] = self.get_lecture()

        context["publishers"] = Group.objects.filter(
            profile__type=GroupProfile.Type.PUBLISHER
        )
        context["viewers"] = Group.objects.filter(
            profile__type=GroupProfile.Type.VIEWER
        )

        contents_qs = (
            self.get_lecture()
            .contents.select_related("slide", "annotation")
            .order_by("order")
        )
        contents = [
            {
                "id": content.id,
                "slide": {
                    "id": content.slide.id,
                    "name": content.slide.name,
                },
                "annotation": (
                    {
                        "id": content.annotation.id,
                        "name": content.annotation.name,
                        "author": content.annotation.author.username,
                    }
                    if content.annotation
                    else None
                ),
            }
            for content in contents_qs
        ]
        context["contents"] = json.dumps(contents)

        base_image_folders = (
            ImageFolder.objects.viewable(self.request.user, parent="root")
            .annotate(type=Value("folder", CharField()))
            .order_by("name")
        )
        root_slides = (
            Slide.objects.viewable(self.request.user, folder="root")
            .annotate(type=Value("image/slide", CharField()))
            .order_by("name")
        )
        items = {
            "children": [
                {
                    "id": folder.id,
                    "name": folder.name,
                }
                for folder in base_image_folders
            ],
            "slides": [
                {
                    "id": slide.id,
                    "name": slide.name,
                }
                for slide in root_slides
            ],
        }
        context["items"] = json.dumps(items)

        return context
