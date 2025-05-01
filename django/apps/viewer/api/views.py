import logging

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.response import Response

from apps.viewer.models import Annotation
from .serializers import AnnotationSerializer

logger = logging.getLogger("django")


class AnnotationViewSet(viewsets.ModelViewSet):
    serializer_class = AnnotationSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        return Annotation.objects.viewable(self.request.user)

    def perform_create(self, serializer):
        serializer.save()
        logger.info(
            f"Annotation '{serializer.instance.name}' created by {self.request.user}"
        )

    def perform_update(self, serializer):
        annotation = self.get_object()
        self._check_edit_permissions(annotation)

        serializer.save()
        logger.info(f"Annotation '{annotation.name}' updated by {self.request.user}")

    def perform_destroy(self, instance):
        self._check_delete_permissions(instance)

        name = instance.name
        instance.delete()
        logger.info(f"Annotation '{name}' deleted by {self.request.user}")

    def retrieve(self, request, *args, **kwargs):
        annotation = self.get_object()
        data = self.get_serializer(annotation).data
        data.update(
            {
                "slide_name": str(annotation.slide) or "-",
                "created_at_formatted": timezone.localtime(
                    annotation.created_at
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at_formatted": timezone.localtime(
                    annotation.updated_at
                ).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return Response(data)

    def _check_delete_permissions(self, annotation):
        if not annotation.is_deletable_by(self.request.user):
            raise PermissionDenied(
                "You don't have permission to delete this annotation."
            )

    def _check_edit_permissions(self, annotation):
        if not annotation.is_editable_by(self.request.user):
            raise PermissionDenied("You don't have permission to edit this annotation.")
