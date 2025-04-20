import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response

from apps.lectures.models import Lecture, LectureFolder
from .serializers import LectureSerializer, LectureFolderSerializer

logger = logging.getLogger("django")


class LectureFolderViewSet(viewsets.ModelViewSet):
    serializer_class = LectureFolderSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        return LectureFolder.objects.viewable(self.request.user)

    def perform_create(self, serializer):
        serializer.save()
        logger.info(
            f"Lecture folder '{serializer.instance.name}' created by {self.request.user}"
        )

    def perform_update(self, serializer):
        folder = serializer.instance
        self._check_edit_permissions(folder)

        serializer.save()
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
                "parent_path": (
                    folder.parent.get_full_path() if folder.parent else "Root"
                ),
                "created_at_formatted": timezone.localtime(folder.created_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "updated_at_formatted": timezone.localtime(folder.updated_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "child_count": folder.children.all().count(),
                "lecture_count": folder.lectures.all().count(),
            }
        )
        return Response(data)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        if not request.user.has_perm("lectures.view_lecturefolder"):
            raise PermissionDenied("You do not have permission to view folders.")

        root_folders = LectureFolder.objects.viewable(request.user, folder="root")
        tree = [self._get_tree_structure(folder) for folder in root_folders]
        return Response(tree)

    def _get_tree_structure(self, folder):
        return {
            "id": folder.id,
            "name": folder.name,
            "children": [
                self._get_tree_structure(sub) for sub in folder.children.all()
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
        serializer.save()
        logger.info(
            f"Lecture '{serializer.instance.name}' created by {self.request.user}"
        )

    def perform_update(self, serializer):
        lecture = serializer.instance
        self._check_edit_permissions(lecture)

        serializer.save()
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
                "folder_name": str(lecture.folder) if lecture.folder else "Root",
                "group_names": [group.name for group in lecture.groups.all()],
                "created_at_formatted": timezone.localtime(lecture.created_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "updated_at_formatted": timezone.localtime(lecture.updated_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "file_count": lecture.get_slides().count(),
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

    @action(detail=True, methods=["post"])
    def duplicate(self, request, *args, **kwargs):
        lecture = self.get_object()
        self._check_edit_permissions(lecture)

        original_name = lecture.name
        # force evaluating queryset with list() to store contents in memory
        contents = list(lecture.contents.all())

        lecture.pk = None
        lecture.name = f"{lecture.name} (copy)"
        lecture.author = lecture.folder.get_owner()
        lecture.save()

        for content in contents:
            content.pk = None
            content.lecture = lecture
            content.save()

        logger.info(f"Lecture '{original_name}' duplicated by {self.request.user}")
        return Response({"detail": "Lecture duplicated successfully."})

    @action(detail=True, methods=["post"])
    def send(self, request, *args, **kwargs):
        target_id = request.data.get("target")
        if not target_id:
            return Response({"target": "Target is required"}, status=400)

        user = request.user
        lecture = self.get_object()
        self._check_edit_permissions(lecture)

        target = get_user_model().objects.get(pk=target_id)
        if not target.base_lecture_folder:
            return Response(
                {"target": f"'{target.username}' doesn't have lecture folder."},
                status=400,
            )

        original_name = lecture.name
        # force evaluating queryset with list() to store contents in memory
        contents = list(lecture.contents.all())

        lecture.pk = None
        lecture.name = f"{lecture.name} (copy)"
        lecture.author = target
        lecture.folder = target.base_lecture_folder
        lecture.save()

        for content in contents:
            content.pk = None
            content.lecture = lecture
            content.save()

        logger.info(f"Lecture '{original_name}' copied to {target} by {user}")
        return Response({"detail": f"Lecture copied to '{target}' successfully."})

    def _check_edit_permissions(self, lecture):
        if not lecture.user_can_edit(self.request.user):
            raise PermissionDenied("You do not have permission to edit this lecture.")
