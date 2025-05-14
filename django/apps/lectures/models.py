import logging

from django.conf import settings
from django.db import models
from django.db.models import Q, Value, BooleanField, Case, When, F

from apps.common.models import (
    ManagerPermissionMixin,
    AbstractFolder,
    ModelPermissionMixin,
    BaseFolderManager,
)

logger = logging.getLogger("django")


class LectureFolderManager(ManagerPermissionMixin, BaseFolderManager):
    def deletable(self, user, *, parent=None):
        if user.is_admin():
            qs = self.filter(parent__isnull=False)
        elif user.is_publisher():
            qs = self.filter(parent__isnull=False, manager=user)
        else:
            qs = self.none()

        # add filter by parent
        if parent:
            if parent == "root":
                qs = qs.filter(parent__isnull=True)
            else:
                qs = qs.filter(parent=parent)

        return qs.distinct()

    def editable(self, user, *, parent=None):
        return self.deletable(user, parent=parent)

    def viewable(self, user, *, parent=None):
        if user.is_admin() or user.is_publisher():
            qs = self.all()
        else:
            qs = self.none()

        # add filter by parent
        if parent:
            if parent == "root":
                qs = qs.filter(parent__isnull=True)
            else:
                qs = qs.filter(parent=parent)

        if user.is_admin():
            is_deletable = Case(
                When(condition=Q(parent__isnull=False), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        else:
            is_deletable = Case(
                When(
                    condition=Q(parent__isnull=False, manager=user),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )

        return qs.distinct().annotate(
            is_deletable=is_deletable, is_editable=F("is_deletable")
        )

    def user_root_folders(self, user):
        result = self.root_nodes()
        if not user.is_admin():
            result = result.filter(user=user)
        return result


class LectureFolder(ModelPermissionMixin, AbstractFolder):
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="managing_lecturefolders",
        blank=True,
        null=True,
    )

    objects = LectureFolderManager()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.is_root_node():
            if self.manager != self.parent.manager:
                self.manager = self.parent.manager
                self.__class__.objects.filter(pk=self.pk).update(manager=self.manager)

    def file_count(self, cumulative=False):
        if cumulative:
            return Lecture.objects.filter(
                folder__in=self.get_descendants(include_self=True)
            ).count()
        return self.lectures.count()

    def is_deletable_by(self, user):
        if self.is_root_node():
            return False
        return self.is_managed_by(user)

    def is_editable_by(self, user):
        return self.is_deletable_by(user)

    def is_viewable_by(self, user):
        return self.is_managed_by(user)

    def is_managed_by(self, user):
        if user.is_admin():
            return True
        return self.manager == user


class LectureManager(ManagerPermissionMixin, models.Manager):
    def deletable(self, user, *, folder=None):
        if user.is_admin():
            qs = self.all()
        elif user.is_publisher():
            qs = self.filter(author=user)
        else:
            qs = self.none()

        # add filter by folder
        if folder:
            if folder == "root":
                qs = qs.filter(folder__isnull=True)
            else:
                qs = qs.filter(folder=folder)

        return qs.distinct()

    def editable(self, user, *, folder=None):
        if user.is_admin():
            qs = self.all()
        elif user.is_publisher():
            qs = self.filter(Q(author=user) | Q(manager=user))
        else:
            qs = self.none()

        # add filter by folder
        if folder:
            if folder == "root":
                qs = qs.filter(folder__isnull=True)
            else:
                qs = qs.filter(folder=folder)

        return qs.distinct()

    def viewable(self, user, *, folder=None):
        if user.is_admin():
            qs = self.all()
        elif user.is_publisher():
            qs = self.filter(
                Q(manager=user) | Q(viewer_groups__in=user.groups.all(), is_active=True)
            )
        elif user.is_viewer():
            qs = self.filter(viewer_groups__in=user.groups.all(), is_active=True)
        else:
            qs = self.none()

        # add filter by folder
        if folder:
            if folder == "root":
                qs = qs.filter(folder__isnull=True)
            else:
                qs = qs.filter(folder=folder)

        if user.is_admin():
            is_deletable = Value(True, BooleanField())
            is_editable = Value(True, BooleanField())
        else:
            is_deletable = Case(
                When(condition=Q(author=user), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
            is_editable = Case(
                When(condition=Q(author=user) | Q(manager=user), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )

        return qs.distinct().annotate(
            is_deletable=is_deletable, is_editable=is_editable
        )


class Lecture(ModelPermissionMixin, models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="lectures",
        blank=True,
        null=True,
    )
    folder = models.ForeignKey(
        "lectures.LectureFolder",
        on_delete=models.CASCADE,
        related_name="lectures",
        blank=False,
        null=False,
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="managing_lectures",
        blank=True,
        null=True,
    )
    viewer_groups = models.ManyToManyField(
        "auth.Group",
        related_name="lectures",
        blank=True,
    )

    objects = LectureManager()

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = self.__class__.objects.get(pk=self.pk)
            if old_instance.manager != self.manager:
                for content in self.contents.all():
                    content.handle_non_viewable()

        super().save(*args, **kwargs)

        if self.folder:
            if self.manager != self.folder.manager:
                self.manager = self.folder.manager
                self.__class__.objects.filter(pk=self.pk).update(manager=self.manager)

    def is_deletable_by(self, user):
        if user.is_admin():
            return True
        return self.author == user

    def is_editable_by(self, user):
        if self.is_deletable_by(user):
            return True

        return self.is_managed_by(user)

    def is_viewable_by(self, user):
        if self.is_editable_by(user):
            return True

        return self.user_is_enrolled(user) and self.is_active

    def is_managed_by(self, user):
        if user.is_admin():
            return True
        return self.manager == user

    def user_is_enrolled(self, user):
        return self.viewer_groups.filter(
            pk__in=user.groups.values_list("id", flat=True)
        ).exists()


class LectureContent(ModelPermissionMixin, models.Model):
    id = models.AutoField(primary_key=True)
    order = models.PositiveSmallIntegerField(help_text="Order inside the lecture")
    created_at = models.DateTimeField(auto_now_add=True)

    lecture = models.ForeignKey(
        "lectures.Lecture",
        on_delete=models.CASCADE,
        related_name="contents",
    )
    slide = models.ForeignKey(
        "images.Slide",
        on_delete=models.CASCADE,
        related_name="lecture_contents",
    )
    annotation = models.ForeignKey(
        "viewer.Annotation",
        on_delete=models.SET_NULL,
        related_name="lecture_contents",
        blank=True,
        null=True,
    )

    class Meta:
        unique_together = ("lecture", "order")
        ordering = ("created_at",)

    def __str__(self):
        return f"Item {self.order} of '{self.lecture}'"

    def save(self, *args, **kwargs):
        if not self.slide.is_viewable_by(self.lecture.manager):
            logger.warning(
                f"Lecture Manager '{self.lecture.manager}' cannot view slide '{self.slide}'"
            )
            return

        if self.annotation:
            if (
                self.annotation.slide != self.slide
                or not self.annotation.is_viewable_by(self.lecture.manager)
            ):
                self.annotation = None

        super().save(*args, **kwargs)

    def is_viewable_by(self, user):
        return self.lecture.is_viewable_by(user)

    def handle_non_viewable(self):
        if not self.slide.is_viewable_by(self.lecture.manager):
            self.delete()
