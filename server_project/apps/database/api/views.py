import logging
import os

from django.core.cache import cache
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
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
        serializer.save()
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
                "parent_path": folder.parent.get_full_path() if folder.parent else "Root",
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

        if request.user.is_admin():
            root_folders = Folder.objects.viewable(request.user, folder="root")
            tree = [
                {
                    "id": None,
                    "name": "Root",
                    "subfolders": [
                        self._get_tree_structure(folder) for folder in root_folders
                    ],
                }
            ]
        else:
            root_folders = Folder.objects.user_base_folders(request.user)
            tree = [self._get_tree_structure(folder) for folder in root_folders]

        return Response(tree)

    @action(detail=True, methods=["get"])
    def items(self, request, pk):
        if not request.user.has_perms(["database.view_folder", "database.view_slide"]):
            raise PermissionDenied("You don't have permission to view folder items.")

        folder = self.get_object()
        subfolders = Folder.objects.viewable(request.user, folder=folder)
        slides = Slide.objects.viewable(request.user, folder=folder)
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
        serializer.save()
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
                "folder_name": str(slide.folder) if slide.folder else "Root",
                "file_details": {
                    "name": os.path.basename(slide.file.name),
                    "size": filesizeformat(slide.file.size),
                    "file_url": reverse("api:slide-file", kwargs={"pk": slide.pk}),
                    "rebuild_url": reverse(
                        "api:slide-rebuild", kwargs={"pk": slide.pk}
                    ),
                    "building": slide.building(),
                },
                "owner_group_name": (
                    slide.get_owner_group().name if slide.get_owner_group() else "admin"
                ),
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
        if not request.user.has_perm("slide_viewer.view_annotation"):
            raise PermissionDenied(
                "You don't have permission to view slide annotations."
            )

        slide = self.get_object()
        self._check_view_permission(slide)

        annotations = Annotation.objects.viewable(request.user, slide=slide)
        return Response(
            AnnotationSerializer(
                annotations, many=True, context={"request": request}
            ).data
        )

    @action(detail=True, methods=["get"])
    def thumbnail(self, request, pk):
        return self._serve_image_file("get_thumbnail_path", "Thumbnail not found.")

    @action(detail=True, methods=["get"])
    def associated_image(self, request, pk):
        return self._serve_image_file(
            "get_associated_image_path", "Associated image not found."
        )

    def _serve_image_file(self, path_method, error_message):
        slide = self.get_object()
        self._check_view_permission(slide)

        path = getattr(slide, path_method)()

        if not os.path.exists(path):
            logger.error(f"{error_message}: {path}")
            return Response({"error": error_message}, status=404)

        return FileResponse(open(path, "rb"), content_type="image/png")

    def _check_edit_permissions(self, slide):
        if not slide.user_can_edit(self.request.user):
            raise PermissionDenied("You don't have permission to edit this slide.")

    def _check_view_permission(self, slide):
        if not slide.user_can_view(self.request.user):
            raise PermissionDenied("You don't have permission to view this slide.")


class DZIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        slide = get_object_or_404(Slide, pk=pk)
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

        slide = get_object_or_404(Slide, pk=pk)
        _check_slide_view_permission(request.user, slide)

        tile_path = os.path.join(
            slide.get_tile_directory(), str(level), f"{col}_{row}.{tile_format}"
        )

        if not os.path.exists(tile_path):
            logger.error(f"Tile not found: {tile_path}")
            return Response({"error": "Tile not found"}, status=404)

        return FileResponse(open(tile_path, "rb"), content_type=f"image/{tile_format}")


class SlideFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        slide = get_object_or_404(Slide, pk=pk)
        _check_slide_view_permission(request.user, slide)

        path = slide.file.path
        if not os.path.exists(path):
            logger.error(f"Slide file not found: {path}")
            return Response({"error": "Slide file not found"}, status=404)

        return FileResponse(slide.file, as_attachment=True)


class RebuildView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        slide = get_object_or_404(Slide, pk=pk)
        _check_slide_edit_permission(request.user, slide)

        if slide.building():
            return Response({"error": "Slide cannot be rebuilt"}, status=400)

        try:
            slide.build_status = slide.BuildStatus.PENDING
            slide.save(update_fields=["build_status"])
            return Response({"status": "Tiles rebuilt successfully"})
        except Exception as e:
            logger.error(f"Failed to rebuild tiles: {str(e)}")
            return Response({"error": str(e)}, status=500)


def _check_slide_view_permission(user, slide):
    cache_key = f"user_{user.id}_slide_{slide.id}_view_permission"

    if cache.get(cache_key):
        return

    if not user.has_perm("database.view_slide") or not slide.user_can_view(user):
        raise PermissionDenied("You don't have permission to view this slide.")

    cache.set(cache_key, True, timeout=10 * 60)  # 10 minutes


def _check_slide_edit_permission(user, slide):
    if not user.has_perm("database.change_slide") or not slide.user_can_edit(user):
        raise PermissionDenied("You don't have permission to edit this slide.")
