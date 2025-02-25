from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
    PermissionRequiredMixin,
)
from django.contrib.auth.models import Group
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView

from apps.accounts.models import GroupProfile
from apps.database.models import Slide, Folder
from apps.lectures.models import Lecture, LectureFolder


class LectureBulletinsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "lectures/lectures.html"
    context_object_name = "lectures"
    permission_required = "lectures.view_lecture"

    def get_queryset(self):
        if self.request.user.is_admin():
            lectures = Lecture.objects.filter(is_active=True)
        else:
            lectures = Lecture.objects.viewable(self.request.user, False)
            lectures |= Lecture.objects.editable(self.request.user).filter(
                is_active=True
            )
        return sorted(lectures, key=lambda x: x.updated_at, reverse=True)

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
            return None
        return get_object_or_404(LectureFolder, id=folder_id)

    def test_func(self):
        if self.request.user.is_admin():
            return True

        current = self.get_folder()
        if current:
            return current.user_can_edit(self.request.user)

        return self.request.user.base_lecture_folder

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_admin() and not self.get_folder():
            folder = self.request.user.base_lecture_folder
            return redirect(
                reverse_lazy("lectures:lecture-database")
                + f"?folder={folder.id or None}"
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        current = self.get_folder()

        if current:
            subfolders = current.subfolders.all()
        else:
            subfolders = LectureFolder.objects.base_folders()

        lectures = Lecture.objects.viewable_by_folder(self.request.user, current)

        for folder in subfolders:
            folder.type = "folder"

        for lecture in lectures:
            lecture.type = "lecture"
            lecture.is_editable = lecture.user_can_edit(self.request.user)

        items = list(subfolders) + list(lectures)
        return sorted(items, key=lambda x: (x.type, x.name.lower()))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current = self.get_folder()
        context["current_folder"] = current
        context["breadcrumbs"] = self._generate_breadcrumbs(current)
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
        contents = self.get_lecture().contents.all()
        return sorted(contents, key=lambda x: x.order)

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
        contents = self.get_lecture().contents.all()
        return sorted(contents, key=lambda x: x.order)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lecture"] = self.get_lecture()
        context["publishers"] = Group.objects.filter(
            profile__type=GroupProfile.TypeChoices.PUBLISHER
        )
        context["viewers"] = Group.objects.filter(
            profile__type=GroupProfile.TypeChoices.VIEWER
        )

        base_folders = Folder.objects.base_folders()
        root_slides = Slide.objects.viewable_by_folder(self.request.user, None)
        for folder in base_folders:
            folder.type = "folder"
        for slide in root_slides:
            slide.type = "slide"

        items = list(base_folders) + list(root_slides)
        context["items"] = sorted(items, key=lambda x: (x.type, x.name.lower()))

        return context
