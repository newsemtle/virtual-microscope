from django.conf import settings
from django.db import models
from django.db.models import Value, BooleanField

from apps.database.models import Slide


class AnnotationManager(models.Manager):
    def editable(self, user, *, slide=None):
        if user.is_admin():
            if slide:
                return self.filter(slide=slide)
            return self.all()
        elif user.is_publisher():
            if slide:
                return self.filter(author=user, slide=slide)
            return self.filter(author=user)

        return self.none()

    def viewable(self, user, *, slide=None):
        extra_viewable = self.none()

        if user.is_publisher():
            if slide:
                extra_viewable |= self.filter(slide=slide)
            else:
                for slide in Slide.objects.viewable(user):
                    extra_viewable |= slide.annotations.all()

        editable = self.editable(user, slide=slide).annotate(
            is_editable=Value(True, BooleanField())
        )
        extra_viewable = extra_viewable.annotate(
            is_editable=Value(False, BooleanField())
        )
        return (editable | extra_viewable).distinct()


class Annotation(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=True)
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the annotation",
    )
    data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="created_by",
        on_delete=models.CASCADE,
        related_name="annotations",
        blank=True,
        null=True,
    )
    slide = models.ForeignKey(
        "database.Slide",
        on_delete=models.CASCADE,
        related_name="annotations",
    )

    objects = AnnotationManager()

    class Meta:
        unique_together = ("name", "author", "slide")
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.name} ({self.author}) | {self.slide}"

    def user_can_edit(self, user):
        if user.is_admin():
            return True
        return self.author == user

    def user_can_view(self, user):
        if user.is_admin():
            return True
        elif user.is_publisher():
            return self.user_can_edit(user) or self.slide.user_can_view(user)
        elif user.is_viewer():
            for content in self.slide.lecture_contents.all():
                if content.user_can_view(user):
                    return True
            return False
        return False
