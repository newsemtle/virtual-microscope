import logging

from django.contrib import messages
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response

from .serializers import LectureSerializer, LectureFolderSerializer
from ..models import Lecture, LectureFolder

logger = logging.getLogger("django")


class LectureFolderViewSet(viewsets.ModelViewSet):
    serializer_class = LectureFolderSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        return LectureFolder.objects.viewable(self.request.user)

    def perform_create(self, serializer):
        folder = serializer.save(author=self.request.user)
        logger.info(f"Lecture folder '{folder.name}' created by {self.request.user}")

    def perform_update(self, serializer):
        folder = self.get_object()
        self._check_edit_permissions(folder)

        folder = serializer.save()
        logger.info(f"Lecture folder '{folder.name}' updated by {self.request.user}")

    def perform_destroy(self, instance):
        self._check_edit_permissions(instance)

        if not instance.is_empty():
            raise PermissionDenied("Folder is not empty. Cannot delete.")

        name = instance.name
        instance.delete()
        logger.info(f"Lecture folder '{name}' deleted by {self.request.user}")

    def retrieve(self, request, *args, **kwargs):
        folder = self.get_object()
        data = self.get_serializer(folder).data
        data.update(
            {
                "parent_name": str(folder.parent) or "-",
                "created_at_formatted": timezone.localtime(folder.created_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "updated_at_formatted": timezone.localtime(folder.updated_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "subfolders_count": folder.subfolders.all().count(),
                "lectures_count": folder.lectures.all().count(),
            }
        )
        return Response(data)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        if not request.user.has_perm("lectures.view_lecturefolder"):
            raise PermissionDenied("You do not have permission to view folders.")

        root_folders = self.get_queryset().filter(parent=None)
        tree = [self._get_tree_structure(folder) for folder in root_folders]
        return Response(tree)

    def _get_tree_structure(self, folder):
        return {
            "id": folder.id,
            "name": folder.name,
            "subfolders": [
                self._get_tree_structure(sub) for sub in folder.subfolders.all()
            ],
        }

    def _check_edit_permissions(self, folder):
        if not folder.user_can_edit(self.request.user):
            raise PermissionDenied("You do not have permission to edit this folder.")


class LectureViewSet(viewsets.ModelViewSet):
    serializer_class = LectureSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        return Lecture.objects.viewable(self.request.user)

    def perform_create(self, serializer):
        lecture = serializer.save(author=self.request.user)
        logger.info(f"Lecture '{lecture.name}' created by {self.request.user}")

    def perform_update(self, serializer):
        lecture = self.get_object()
        self._check_edit_permissions(lecture)

        lecture = serializer.save()
        logger.info(f"Lecture '{lecture.name}' updated by {self.request.user}")

    def perform_destroy(self, instance):
        self._check_edit_permissions(instance)

        name = instance.name
        instance.delete()
        logger.info(f"Lecture '{name}' deleted by {self.request.user}")

    def retrieve(self, request, *args, **kwargs):
        lecture = self.get_object()
        data = self.get_serializer(lecture).data
        data.update(
            {
                "folder_name": str(lecture.folder) or "-",
                "group_names": [group.name for group in lecture.groups.all()],
                "created_at_formatted": timezone.localtime(lecture.created_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "updated_at_formatted": timezone.localtime(lecture.updated_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "slides_count": lecture.get_slides().count(),
            }
        )
        return Response(data)

    @action(detail=True, methods=["patch"])
    def toggle_activity(self, request, *args, **kwargs):
        lecture = self.get_object()

        if not request.user.has_perm("lectures.change_lecture"):
            raise PermissionDenied("You do not have permission to edit lectures.")
        if not lecture.user_can_edit(request.user):
            raise PermissionDenied("You do not have permission to edit this lecture.")

        lecture.is_active = not lecture.is_active
        lecture.save()

        logger.info(f"Lecture '{lecture.name}' activity toggled by {self.request.user}")
        return Response(
            {
                "is_active": lecture.is_active,
                "updated_at_formatted": timezone.localtime(lecture.updated_at).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            }
        )

    def _check_edit_permissions(self, lecture):
        if not lecture.user_can_edit(self.request.user):
            raise PermissionDenied("You do not have permission to edit this lecture.")