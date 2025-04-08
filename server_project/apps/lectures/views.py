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
from django.views.generic import ListView

from apps.accounts.models import GroupProfile
from apps.database.models import Slide, Folder
from apps.lectures.models import Lecture, LectureFolder


class LectureBulletinsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "lectures/lecture_bulletins.html"
    context_object_name = "lectures"
    permission_required = "lectures.view_lecture"

    def get_queryset(self):
        user = self.request.user
        lectures = (
            Lecture.objects.viewable(user)
            .filter(is_active=True)
            .order_by("-updated_at")
        )
        return lectures

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for lecture in context["lectures"]:
            lecture.is_editable = lecture.user_can_edit(self.request.user)
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
            return current.user_can_view(user)
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
            raise PermissionDenied("You do not have permission to access this page.")

    def get_queryset(self):
        user = self.request.user
        current = self.get_folder()

        if not current:
            current = "root"
        subfolders = (
            LectureFolder.objects.viewable(user, folder=current)
            .annotate(type=Value("folder", CharField()))
            .order_by("name")
        )
        lectures = (
            Lecture.objects.viewable(user, folder=current)
            .annotate(type=Value("lecture", CharField()))
            .order_by("name")
        )

        return list(subfolders) + list(lectures)

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
            breadcrumbs.append({"id": "", "name": "Root"})

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
        return lecture.user_can_view(self.request.user)

    def get_queryset(self):
        contents = self.get_lecture().contents.all().order_by("order")
        return contents

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lecture"] = self.get_lecture()
        context["editable"] = self.get_lecture().user_can_edit(self.request.user)
        return context


class LectureEditView(
    LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, ListView
):
    template_name = "lectures/lecture_edit.html"
    context_object_name = "contents"
    permission_required = ["lectures.change_lecture", "database.view_slide"]

    def get_lecture(self):
        lecture_id = self.kwargs.get("lecture_id")
        return Lecture.objects.get(id=lecture_id)

    def test_func(self):
        lecture = self.get_lecture()
        return lecture.user_can_edit(self.request.user)

    def get_queryset(self):
        contents = self.get_lecture().contents.all().order_by("order")
        return contents

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lecture"] = self.get_lecture()
        context["publishers"] = Group.objects.filter(
            profile__type=GroupProfile.Type.PUBLISHER
        )
        context["viewers"] = Group.objects.filter(
            profile__type=GroupProfile.Type.VIEWER
        )

        base_folders = (
            Folder.objects.viewable(self.request.user, folder="root")
            .annotate(type=Value("folder", CharField()))
            .order_by("name")
        )
        root_slides = (
            Slide.objects.viewable(self.request.user, folder="root")
            .annotate(type=Value("image/slide", CharField()))
            .order_by("name")
        )
        context["items"] = list(base_folders) + list(root_slides)

        return context
