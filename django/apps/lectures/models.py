import logging

from django.conf import settings
from django.db import models
from django.db.models import Q, Value, BooleanField, Case, When, F
from django.utils.translation import gettext_lazy as _lazy, pgettext_lazy

from apps.core.models import (
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
        verbose_name=_lazy("manager"),
        on_delete=models.SET_NULL,
        related_name="managing_lecturefolders",
        blank=True,
        null=True,
    )

    objects = LectureFolderManager()

    def save(self, *args, **kwargs):
        handle_manager = False

        # manager
        if not self.is_root_node() and self.manager != self.parent.manager:
            self.manager = self.parent.manager

        if self.pk:
            old = self.__class__.objects.get(pk=self.pk)

            handle_manager = self.manager != old.manager

        super().save(*args, **kwargs)

        if handle_manager:
            self._update_descendants_and_lectures_manager()

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

    def _update_descendants_and_lectures_manager(self):
        descendants = self.get_descendants(include_self=True)
        descendants.update(manager=self.manager)

        lectures = (
            Lecture.objects.filter(folder__in=descendants)
            .select_related("manager")
            .only("id", "manager_id")
        )
        lectures.update(manager=self.manager)
        for lecture in lectures:
            LectureContent.objects.handle_unavailable_by_lecture(lecture)


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
                Q(manager=user) | Q(viewer_groups__in=user.groups.all(), is_open=True)
            )
        elif user.is_viewer():
            qs = self.filter(viewer_groups__in=user.groups.all(), is_open=True)
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
    name = models.CharField(_lazy("name"), max_length=250)
    description = models.TextField(_lazy("description"), blank=True, null=True)
    is_open = models.BooleanField(
        _lazy("open"),
        default=False,
        help_text=_lazy("Whether the lecture is open for viewer groups or not."),
    )
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
        verbose_name=_lazy("author"),
        on_delete=models.SET_NULL,
        related_name="lectures",
        blank=True,
        null=True,
    )
    folder = models.ForeignKey(
        "lectures.LectureFolder",
        verbose_name=_lazy("folder"),
        on_delete=models.CASCADE,
        related_name="lectures",
        blank=False,
        null=False,
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_lazy("manager"),
        on_delete=models.SET_NULL,
        related_name="managing_lectures",
        blank=True,
        null=True,
    )
    viewer_groups = models.ManyToManyField(
        "auth.Group",
        verbose_name=_lazy("viewer groups"),
        related_name="lectures",
        blank=True,
        help_text=_lazy("The groups that can view the lecture."),
    )

    objects = LectureManager()

    class Meta:
        verbose_name = _lazy("lecture")
        verbose_name_plural = _lazy("lectures")
        ordering = ("created_at",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        handle_manager = False

        # manager
        if self.folder and self.manager != self.folder.manager:
            self.manager = self.folder.manager

        if self.pk:
            old = self.__class__.objects.get(pk=self.pk)

            handle_manager = self.manager != old.manager

        super().save(*args, **kwargs)

        if handle_manager:
            LectureContent.objects.handle_unavailable_by_lecture(self)

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

        return self.user_is_enrolled(user) and self.is_open

    def is_managed_by(self, user):
        if user.is_admin():
            return True
        return self.manager == user

    def user_is_enrolled(self, user):
        return self.viewer_groups.filter(
            pk__in=user.groups.values_list("id", flat=True)
        ).exists()

    def image_count(self):
        return self.contents.count()


class LectureContentManager(models.Manager):
    def handle_unavailable_by_lecture(self, lecture):
        manager = lecture.manager
        for content in self.filter(lecture=lecture).select_related("slide"):
            if not content.slide.is_viewable_by(manager, include_lecture=False):
                content.delete()

    def handle_unavailable_by_slide(self, slide):
        for content in self.filter(slide=slide).select_related("lecture__manager"):
            if not slide.is_viewable_by(content.lecture.manager, include_lecture=False):
                content.delete()

    def handle_unavailable_by_user(self, user):
        for lecture in user.managing_lectures.all():
            self.handle_unavailable_by_lecture(lecture)


class LectureContent(ModelPermissionMixin, models.Model):
    id = models.AutoField(primary_key=True)
    order = models.PositiveSmallIntegerField(
        _lazy("order"),
        help_text=_lazy("Order inside the lecture"),
    )

    lecture = models.ForeignKey(
        "lectures.Lecture",
        verbose_name=_lazy("lecture"),
        on_delete=models.CASCADE,
        related_name="contents",
    )
    slide = models.ForeignKey(
        "images.Slide",
        verbose_name=_lazy("slide"),
        on_delete=models.CASCADE,
        related_name="lecture_contents",
    )
    annotation = models.ForeignKey(
        "viewer.Annotation",
        verbose_name=_lazy("annotation"),
        on_delete=models.SET_NULL,
        related_name="lecture_contents",
        blank=True,
        null=True,
    )

    objects = LectureContentManager()

    class Meta:
        verbose_name = _lazy("lecture content")
        verbose_name_plural = _lazy("lecture contents")

    def __str__(self):
        return f"Item {self.order} of '{self.lecture}'"

    def save(self, *args, **kwargs):
        # slide
        if not self.slide.is_viewable_by(self.lecture.manager, include_lecture=False):
            if self.pk:
                self.delete()
            return

        # annotation
        if self.annotation:
            if (
                self.annotation.slide != self.slide
                or not self.annotation.is_viewable_by(self.lecture.manager)
            ):
                self.annotation = None

        super().save(*args, **kwargs)

    def is_viewable_by(self, user):
        return self.lecture.is_viewable_by(user)
