import logging
import os

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.slide_viewer.api.serializers import AnnotationSerializer
from apps.slide_viewer.models import Annotation
from .serializers import SlideSerializer, FolderSerializer
from ..models import Slide, Folder

logger = logging.getLogger("django")


class FolderViewSet(viewsets.ModelViewSet):
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        return Folder.objects.viewable(self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        logger.info(
            f"Folder '{serializer.instance.name}' created by {self.request.user}"
        )

    def perform_update(self, serializer):
        folder = self.get_object()
        self._check_edit_permissions(folder)

        serializer.save()
        logger.info(f"Folder '{folder.name}' updated by {self.request.user}")

    def perform_destroy(self, instance):
        self._check_edit_permissions(instance)

        if not instance.is_empty():
            raise PermissionDenied("Folder is not empty. Cannot delete.")

        name = instance.name
        instance.delete()
        logger.info(f"Folder '{name}' deleted by {self.request.user}")

    def retrieve(self, request, *args, **kwargs):
        folder = self.get_object()
        data = self.get_serializer(folder).data
        data.update(
            {
                "parent_path": folder.parent.get_full_path() if folder.parent else "-",
                "created_at_formatted": timezone.localtime(folder.created_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "updated_at_formatted": timezone.localtime(folder.updated_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "subfolders_count": folder.subfolders.all().count(),
                "slides_count": folder.slides.all().count(),
            }
        )
        return Response(data)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        if not request.user.has_perm("database.view_folder"):
            raise PermissionDenied("You don't have permission to view folders.")

        root_folders = self.get_queryset().filter(parent=None)
        tree = [self._get_tree_structure(folder) for folder in root_folders]

        if request.user.is_admin():
            tree = [
                {
                    "id": None,
                    "name": "Root",
                    "subfolders": tree,
                }
            ]
        return Response(tree)

    @action(detail=True, methods=["get"])
    def items(self, request, pk):
        if not request.user.has_perms(["database.view_folder", "database.view_slide"]):
            raise PermissionDenied("You don't have permission to view folder items.")

        folder = self.get_object()
        subfolders = folder.subfolders.all()
        slides = Slide.objects.viewable_by_folder(request.user, folder)
        return Response(
            {
                "subfolders": FolderSerializer(subfolders, many=True).data,
                "slides": SlideSerializer(slides, many=True).data,
            }
        )

    def _check_edit_permissions(self, folder):
        if not folder.user_can_edit(self.request.user):
            raise PermissionDenied("You don't have permission to edit this folder.")

    def _get_tree_structure(self, folder):
        return {
            "id": folder.id,
            "name": folder.name,
            "subfolders": [
                self._get_tree_structure(sub) for sub in folder.subfolders.all()
            ],
        }


class SlideViewSet(viewsets.ModelViewSet):
    serializer_class = SlideSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        return Slide.objects.viewable(self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        logger.info(
            f"Slide '{serializer.instance.name}' created by {self.request.user}"
        )

    def perform_update(self, serializer):
        slide = self.get_object()
        self._check_edit_permissions(slide)

        serializer.save()
        logger.info(f"Slide '{slide.name}' updated by {self.request.user}")

    def perform_destroy(self, instance):
        self._check_edit_permissions(instance)

        name = instance.name
        instance.delete()
        logger.info(f"Slide '{name}' deleted by {self.request.user}")

    def retrieve(self, request, *args, **kwargs):
        slide = self.get_object()
        data = self.get_serializer(slide).data
        data.update(
            {
                "folder_name": str(slide.folder) or "-",
                "file_name": slide.file.name,
                "created_at_formatted": timezone.localtime(slide.created_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "updated_at_formatted": timezone.localtime(slide.updated_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }
        )
        return Response(data)

    @action(detail=True, methods=["get"])
    def annotations(self, request, pk):
        if not request.user.has_perm("database.view_annotation"):
            raise PermissionDenied(
                "You don't have permission to view slide annotations."
            )

        slide = self.get_object()
        annotations = Annotation.objects.viewable_by_slide(request.user, slide)
        return Response(AnnotationSerializer(annotations, many=True).data)

    @action(detail=True, methods=["get"])
    def thumbnail(self, request, pk):
        return self._serve_image_file("get_thumbnail_path", "Thumbnail not found.")

    @action(detail=True, methods=["get"])
    def associated_image(self, request, pk):
        return self._serve_image_file(
            "get_associated_image_path", "Associated image not found."
        )

    def _check_edit_permissions(self, slide):
        if not slide.user_can_edit(self.request.user):
            raise PermissionDenied("You don't have permission to edit this slide.")

    def _serve_image_file(self, path_method, error_message):
        slide = self.get_object()

        if not slide.user_can_view(self.request.user):
            raise PermissionDenied("You don't have permission to view this slide.")

        path = getattr(slide, path_method)()

        if not os.path.exists(path):
            logger.error(f"{error_message}: {path}")
            return Response({"error": error_message}, status=404)

        return FileResponse(open(path, "rb"), content_type="image/png")


class DZIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        slide = get_object_or_404(Slide, id=pk)
        _check_slide_view_permission(request.user, slide)

        path = slide.get_dzi_path()

        if not os.path.exists(path):
            logger.error(f"DZI file not found: {path}")
            return Response({"error": "DZI file not found"}, status=404)

        return FileResponse(open(path, "rb"), content_type="application/xml")


class TileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, level, col, row, tile_format):
        if tile_format not in {"jpeg", "png"}:
            return Response({"error": "Unsupported format"}, status=400)

        slide = get_object_or_404(Slide, id=pk)
        _check_slide_view_permission(request.user, slide)

        tile_path = os.path.join(
            slide.get_tile_directory(), str(level), f"{col}_{row}.{tile_format}"
        )

        if not os.path.exists(tile_path):
            logger.error(f"Tile not found: {tile_path}")
            return Response({"error": "Tile not found"}, status=404)

        return FileResponse(open(tile_path, "rb"), content_type=f"image/{tile_format}")


def _check_slide_view_permission(user, slide):
    if not user.has_perm("database.view_slide"):
        raise PermissionDenied("You don't have permission to view slides.")
    if not slide.user_can_view(user):
        raise PermissionDenied("You don't have permission to view this slide.")
