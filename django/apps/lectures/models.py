from django.conf import settings
from django.db import models
from django.db.models import Q, Value, BooleanField


class LectureFolderManager(models.Manager):
    def editable(self, user, *, folder=None):
        if folder == "root":
            return self.none()

        if user.is_admin():
            if folder:
                return self.filter(parent=folder)
            return self.all().filter(parent__isnull=False)
        elif user.is_publisher():
            if folder:
                if folder.is_owner(user):
                    return self.filter(parent=folder)
                else:
                    return self.none()
            return self.descendants_iter(user.base_lecture_folder)

        return self.none()

    def viewable(self, user, *, folder=None):
        extra_viewable = self.none()

        if user.is_admin():
            if folder == "root" or not folder:
                extra_viewable |= self.filter(parent__isnull=True)
        elif user.is_publisher():
            if folder == "root" or not folder:
                extra_viewable |= LectureFolder.objects.filter(
                    pk=user.base_lecture_folder.pk
                )
        else:
            return self.none()

        editable = self.editable(user, folder=folder).annotate(
            is_editable=Value(True, BooleanField())
        )
        extra_viewable = extra_viewable.annotate(
            is_editable=Value(False, BooleanField())
        )
        return (editable | extra_viewable).distinct()

    def descendants_iter(self, folder):
        descendants = folder.children.all()
        for subfolder in descendants:
            descendants |= self.descendants_iter(subfolder)
        return descendants


class LectureFolder(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column="created_by",
        related_name="lecture_folders",
        blank=True,
        null=True,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
    )

    objects = LectureFolderManager()

    class Meta:
        unique_together = ("name", "parent")
        ordering = ("name",)

    def __str__(self):
        return self.get_full_path()

    def delete(self, *args, **kwargs):
        if not self.is_empty():
            raise Exception("Folder is not empty. Cannot delete.")
        super().delete(*args, **kwargs)

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()}/{self.name}"
        return self.name

    def is_base_folder(self):
        return self.parent is None

    def get_base_folder(self):
        current_folder = self
        while current_folder.parent:
            current_folder = current_folder.parent
        return current_folder

    def get_owner(self):
        return self.get_base_folder().user

    def is_owner(self, user):
        if user.is_admin():
            return True
        return self.get_owner() == user

    def user_can_edit(self, user):
        if self.is_base_folder():
            return False
        if user.is_admin():
            return True
        return self.get_owner() == user

    def user_can_view(self, user):
        if user.is_admin():
            return True
        elif user.is_publisher():
            return self.get_owner() == user
        return False

    def is_empty(self):
        if self.lectures.exists():
            return False
        for subfolder in self.children.all():
            if not subfolder.is_empty():
                return False
        return True

    def is_children(self, folder):
        current_folder = folder.parent
        while current_folder:
            if current_folder == self:
                return True
            current_folder = current_folder.parent
        return False


class LectureManager(models.Manager):
    def editable(self, user, *, folder=None):
        q = Q()

        if user.is_admin():
            pass
        elif user.is_publisher():
            q &= Q(author=user)
        else:
            return self.none()

        if folder:
            if folder == "root":
                q &= Q(folder__isnull=True)
            else:
                q &= Q(folder=folder)

        return self.filter(q)

    def viewable(self, user, *, folder=None):
        q = Q()

        if user.is_admin():
            pass
        elif user.is_publisher() or user.is_viewer():
            q &= Q(groups__in=user.groups.all()) & Q(is_active=True)
        else:
            return self.none()

        if folder:
            if folder == "root":
                q &= Q(folder__isnull=True)
            else:
                q &= Q(folder=folder)

        editable = self.editable(user, folder=folder).annotate(
            is_editable=Value(True, BooleanField())
        )
        extra_viewable = self.filter(q).annotate(
            is_editable=Value(False, BooleanField())
        )

        return (editable | extra_viewable).distinct()


class Lecture(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(
        blank=True,
        null=True,
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column="created_by",
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
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="lectures",
        blank=True,
    )
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LectureManager()

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = Lecture.objects.get(pk=self.pk)
            if old_instance.author != self.author:
                self.update_lecture_contents()

        super().save(*args, **kwargs)

    def user_can_edit(self, user):
        if user.is_admin():
            return True
        return self.author == user

    def user_is_enrolled(self, user):
        for group in self.groups.all():
            if group in user.groups.all():
                return True
        return False

    def user_can_view(self, user):
        return self.user_can_edit(user) or (
            self.user_is_enrolled(user) and self.is_active
        )

    def get_slides(self):
        from apps.images.models import Slide

        return Slide.objects.filter(Q(id__in=self.contents.values("slide")))

    def update_lecture_contents(self):
        for lecture_content in self.contents.all():
            lecture_content.update()


class LectureContent(models.Model):
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
        blank=True,
        null=True,
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
        return f"{self.order} of {self.lecture}"

    def save(self, *args, **kwargs):
        if not self.slide.user_can_view(self.lecture.author):
            return

        if self.annotation:
            if (
                self.annotation.slide != self.slide
                or not self.annotation.user_can_view(self.lecture.author)
            ):
                self.annotation = None

        super().save(*args, **kwargs)

    def user_can_view(self, user):
        return self.lecture.user_can_view(user)

    def update(self):
        if not self.slide.user_can_view(self.lecture.author):
            self.delete()
