from django.conf import settings
from django.db import models
from django.db.models import Value, BooleanField, Q, Case, When, F
from django.utils.translation import gettext_lazy as _lazy, pgettext_lazy

from apps.core.models import ManagerPermissionMixin, ModelPermissionMixin
from apps.images.models import Slide
from apps.lectures.models import Lecture


class AnnotationManager(ManagerPermissionMixin, models.Manager):
    def deletable(self, user, *, slide=None):
        if user.is_admin():
            qs = self.all()
        elif user.is_publisher():
            qs = self.filter(author=user)
        else:
            qs = self.none()

        # add filter by slide
        if slide:
            qs = qs.filter(slide=slide)

        return qs.distinct()

    def editable(self, user, *, slide=None):
        return self.deletable(user, slide=slide)

    def viewable(self, user, *, slide=None, include_lecture=True):
        if user.is_admin():
            qs = self.all()
        elif user.is_publisher():
            qs = self.filter(
                slide_id__in=Slide.objects.viewable(
                    user, include_lecture=False
                ).values_list("pk", flat=True)
            )
        else:
            qs = self.none()

        if include_lecture and (user.is_publisher() or user.is_viewer()):
            qs |= self.filter(
                lecture_contents__lecture_id__in=Lecture.objects.viewable(
                    user
                ).values_list("id", flat=True)
            )

        # add filter by slide
        if slide:
            qs = qs.filter(slide=slide)

        if user.is_admin():
            is_deletable = Value(True, BooleanField())
        else:
            is_deletable = Case(
                When(condition=Q(author=user), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )

        return qs.distinct().annotate(
            is_deletable=is_deletable, is_editable=F("is_deletable")
        )


class Annotation(ModelPermissionMixin, models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(
        blank=True,
        null=True,
        help_text=_lazy("Description of the annotation"),
    )
    data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(
        pgettext_lazy("date", "created"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        pgettext_lazy("date", "updated"),
        auto_now=True,
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="annotations",
        blank=True,
        null=True,
    )
    slide = models.ForeignKey(
        "images.Slide",
        on_delete=models.CASCADE,
        related_name="annotations",
    )

    objects = AnnotationManager()

    class Meta:
        unique_together = ("name", "author", "slide")
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.name} ({self.author}) | {self.slide}"

    def is_deletable_by(self, user):
        if user.is_admin():
            return True
        return self.author == user

    def is_editable_by(self, user):
        return self.is_deletable_by(user)

    def is_viewable_by(self, user, *, include_lecture=True):
        if self.is_editable_by(user):
            return True

        if user.is_admin():
            return True
        elif user.is_publisher():
            if self.slide.is_viewable_by(user):
                return True

        if include_lecture and (user.is_publisher() or user.is_viewer()):
            return any(
                content.is_viewable_by(user) for content in self.lecture_contents.all()
            )

        return False
