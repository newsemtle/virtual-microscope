from django.conf import settings
from django.db import models


class LectureFolderManager(models.Manager):
    def base_folders(self):
        return self.filter(parent__isnull=True)

    def editable_base_folders(self, user):
        if user.is_admin():
            return self.base_folders()
        return self.base_folders().filter(user=user)

    def editable(self, user):
        if user.is_admin():
            return self.all()
        folders = self.editable_base_folders(user)
        for folder in self.editable_base_folders(user):
            folders |= self.descendents(folder)
        return folders

    def viewable(self, user):
        return self.editable(user)

    def descendents(self, folder):
        folders = folder.subfolders.all()
        for subfolder in folder.subfolders.all():
            folders |= self.descendents(subfolder)
        return folders


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
        related_name="subfolders",
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

    def user_can_edit(self, user):
        if user.is_admin():
            return True
        return self.get_owner() == user

    def is_empty(self):
        if self.lectures.exists():
            return False
        for subfolder in self.subfolders.all():
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
    def root_lectures(self):
        """Get lectures that aren't in any folder"""
        return self.filter(parent__isnull=True)

    def editable(self, user):
        if user.is_admin():
            return self.all()
        return self.filter(author=user)

    def viewable(self, user, include_editable=True):
        if user.is_admin():
            return self.all()
        viewable = self.filter(groups__in=user.groups.all(), is_active=True)
        if include_editable:
            viewable |= self.editable(user)
        return viewable

    def editable_by_folder(self, user, folder):
        if not folder:
            if user.is_admin():
                return self.filter(folder__isnull=True)
            else:
                return self.editable(user).filter(folder__isnull=True)
        if user.is_admin():
            return self.filter(folder=folder)
        return self.editable(user).filter(folder=folder)

    def viewable_by_folder(self, user, folder, include_editable=True):
        if not folder:
            if user.is_admin():
                return self.filter(folder__isnull=True)
            else:
                return self.viewable(user, include_editable).filter(folder__isnull=True)
        if user.is_admin():
            return self.filter(folder=folder)
        return self.viewable(user, include_editable).filter(folder=folder)


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
        return self.contents.values_list("slide", flat=True)


class LectureContent(models.Model):
    id = models.AutoField(primary_key=True)
    lecture = models.ForeignKey(
        "lectures.Lecture",
        on_delete=models.CASCADE,
        related_name="contents",
        blank=True,
        null=True,
    )
    order = models.PositiveSmallIntegerField(help_text="Order inside the lecture")
    slide = models.ForeignKey(
        "database.Slide",
        on_delete=models.CASCADE,
        related_name="lecture_contents",
        blank=True,
        null=True,
    )
    annotation = models.ForeignKey(
        "slide_viewer.Annotation",
        on_delete=models.SET_NULL,
        related_name="lecture_contents",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("lecture", "order")
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.order} of {self.lecture}"

    def save(self, *args, **kwargs):
        if not self.slide.user_can_view(self.lecture.author):
            raise ValueError("Slide must be viewable by the lecture author")
        if self.annotation:
            if (
                self.annotation.slide != self.slide
                or not self.annotation.user_can_view(self.lecture.author)
            ):
                self.annotation = None
        super().save(*args, **kwargs)
