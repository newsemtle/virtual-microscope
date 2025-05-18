import logging
import os

from django.core.cache import cache
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.translation import gettext as _, gettext_noop as _noop
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.images.models import Slide, ImageFolder
from apps.viewer.api.serializers import AnnotationSerializer
from apps.viewer.models import Annotation
from .serializers import SlideSerializer, ImageFolderSerializer

logger = logging.getLogger("django")


class ImageFolderViewSet(viewsets.ModelViewSet):
    serializer_class = ImageFolderSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        return ImageFolder.objects.viewable(self.request.user)

    def perform_create(self, serializer):
        serializer.save()
        logger.info(
            f"Folder '{serializer.instance.name}' created by {self.request.user}"
        )

    def perform_update(self, serializer):
        folder = serializer.instance
        self._check_edit_permissions(folder)

        serializer.save()
        logger.info(f"Folder '{folder.name}' updated by {self.request.user}")

    def perform_destroy(self, instance):
        self._check_delete_permissions(instance)

        if instance.file_count() > 0:
            raise PermissionDenied(_("Folder is not empty. Cannot delete."))

        name = instance.name
        instance.delete()
        logger.info(f"Folder '{name}' deleted by {self.request.user}")

    def retrieve(self, request, *args, **kwargs):
        folder = self.get_object()
        data = self.get_serializer(folder).data
        data.update(
            {
                "parent_path": (
                    folder.parent.get_full_path() if folder.parent else _("Root")
                ),
                "child_count": folder.children.count(),
                "file_count": folder.file_count(cumulative=False),
                "total_file_count": folder.file_count(cumulative=True),
            }
        )
        return Response(data)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        user = request.user
        if not user.has_perm("images.view_imagefolder"):
            raise PermissionDenied(_("You don't have permission to view folders."))

        root_folders = ImageFolder.objects.user_root_folders(user)
        tree = [self._serialize_folders(folder) for folder in root_folders]
        if user.is_admin():
            tree = [{"id": None, "name": _("Root"), "children": tree}]

        return Response(tree)

    @action(detail=True, methods=["get"])
    def items(self, request, pk):
        if not request.user.has_perms(["images.view_imagefolder", "images.view_slide"]):
            raise PermissionDenied(_("You don't have permission to view folder items."))

        folder = self.get_object()
        children = ImageFolder.objects.viewable(request.user, parent=folder)
        slides = Slide.objects.viewable(request.user, folder=folder)
        return Response(
            {
                "children": ImageFolderSerializer(children, many=True).data,
                "slides": SlideSerializer(slides, many=True).data,
            }
        )

    def _check_delete_permissions(self, folder):
        if not folder.is_deletable_by(self.request.user):
            raise PermissionDenied(
                _("You don't have permission to delete this folder.")
            )

    def _check_edit_permissions(self, folder):
        if not folder.is_editable_by(self.request.user):
            raise PermissionDenied(_("You don't have permission to edit this folder."))

    def _serialize_folders(self, folder):
        return {
            "id": folder.id,
            "name": folder.name,
            "children": [self._serialize_folders(sub) for sub in folder.children.all()],
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
        slide = serializer.instance
        self._check_edit_permissions(slide)

        serializer.save()
        logger.info(f"Slide '{slide.name}' updated by {self.request.user}")

    def perform_destroy(self, instance):
        self._check_delete_permissions(instance)

        name = instance.name
        instance.delete()
        logger.info(f"Slide '{name}' deleted by {self.request.user}")

    def retrieve(self, request, *args, **kwargs):
        slide = self.get_object()
        data = self.get_serializer(slide).data
        data.update(
            {
                "folder_name": str(slide.folder) if slide.folder else _("Root"),
                "file_details": {
                    "name": os.path.basename(slide.file.name),
                    "size": filesizeformat(slide.file.size),
                    "file_url": reverse("api:slide-file", kwargs={"pk": slide.pk}),
                    "rebuild_url": reverse(
                        "api:slide-rebuild", kwargs={"pk": slide.pk}
                    ),
                    "building": slide.building(),
                },
                "associated_image_names": slide.associated_image_names,
            }
        )
        return Response(data)

    @action(detail=True, methods=["get"])
    def annotations(self, request, pk):
        if not request.user.has_perm("viewer.view_annotation"):
            raise PermissionDenied(
                _("You don't have permission to view slide annotations.")
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
        slide = self.get_object()
        self._check_view_permission(slide)

        path = slide.thumbnail_path

        if not os.path.exists(path):
            return Response({"detail": _("Thumbnail not found.")}, status=404)

        return FileResponse(open(path, "rb"), content_type="image/png")

    @action(
        detail=True, methods=["get"], url_path="associated_image/(?P<filename>[^/]+)"
    )
    def associated_image(self, request, pk, filename):
        slide = self.get_object()
        self._check_view_permission(slide)

        file_path = os.path.join(slide.associated_image_directory_path, filename)

        if not os.path.exists(file_path):
            return Response({"detail": _("Image not found.")}, status=404)

        return FileResponse(open(file_path, "rb"), content_type="image/png")

    def _check_delete_permissions(self, slide):
        if not slide.is_deletable_by(self.request.user):
            raise PermissionDenied(_("You don't have permission to delete this slide."))

    def _check_edit_permissions(self, slide):
        if not slide.is_editable_by(self.request.user):
            raise PermissionDenied(_("You don't have permission to edit this slide."))

    def _check_view_permission(self, slide):
        if not slide.is_viewable_by(self.request.user):
            raise PermissionDenied(_("You don't have permission to view this slide."))


class SlideDBSearchAPIView(ListAPIView):
    serializer_class = SlideSerializer
    permission_classes = [IsAuthenticated]
    # filterset_class = SlideFilter
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "=manager_group__name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Slide.objects.viewable(self.request.user, include_lecture=False)


class SlideDZIAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        slide = get_object_or_404(Slide, pk=pk)
        _check_slide_view_permission(request.user, slide)

        path = slide.dzi_path

        if not os.path.exists(path):
            message = _noop("DZI file not found")
            logger.error(f"{message}: {path}")
            return Response({"detail": _("DZI file not found")}, status=404)

        return FileResponse(open(path, "rb"), content_type="application/xml")


class SlideTileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, level, col, row, tile_format):
        slide = get_object_or_404(Slide, pk=pk)
        _check_slide_view_permission(request.user, slide)

        tile_path = os.path.join(
            slide.tile_directory_path, str(level), f"{col}_{row}.{tile_format}"
        )

        if not os.path.exists(tile_path):
            return Response({"detail": _("Tile not found")}, status=404)

        response = FileResponse(
            open(tile_path, "rb"), content_type=f"image/{tile_format}"
        )
        response["Cache-Control"] = "public, max-age=86400"
        return response


class SlideFileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        slide = get_object_or_404(Slide, pk=pk)
        _check_slide_edit_permission(request.user, slide)

        path = slide.file.path
        if not os.path.exists(path):
            return Response({"detail": _("Slide file not found")}, status=404)

        return FileResponse(slide.file, as_attachment=True)


class SlideRebuildAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        slide = get_object_or_404(Slide, pk=pk)
        _check_slide_edit_permission(request.user, slide)

        if slide.building():
            return Response({"detail": _("Slide cannot be repaired")}, status=400)

        try:
            slide.build_status = slide.BuildStatus.PENDING
            slide.save(update_fields=["build_status"])
            return Response({"detail": _("Slide repaired successfully")})
        except Exception as e:
            message = _noop("Failed to rebuild slide")
            logger.error(f"{message}: {str(e)}")
            return Response({"detail": _(message)}, status=500)


def _check_slide_view_permission(user, slide):
    cache_key = f"user_{user.id}_slide_{slide.id}_view_permission"

    if cache.get(cache_key):
        return

    if not user.has_perm("images.view_slide") or not slide.is_viewable_by(user):
        raise PermissionDenied(_("You don't have permission to view this slide."))

    cache.set(cache_key, True, timeout=60 * 10)  # 10 minutes


def _check_slide_edit_permission(user, slide):
    if not user.has_perm("images.change_slide") or not slide.is_editable_by(user):
        raise PermissionDenied(_("You don't have permission to edit this slide."))
