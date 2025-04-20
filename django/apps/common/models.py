from django.conf import settings
from django.db import models
from django.db.models import AutoField
from mptt.managers import TreeManager
from mptt.models import MPTTModel, TreeForeignKey


class BaseFolderManager(TreeManager):
    def deletable(self, user, *, folder=None):
        raise NotImplementedError("Subclasses must implement `deletable()` method.")

    def editable(self, user, *, folder=None):
        raise NotImplementedError("Subclasses must implement `editable()` method.")

    def viewable(self, user, *, folder=None):
        raise NotImplementedError("Subclasses must implement `viewable()` method.")


class AbstractFolder(MPTTModel):
    id = AutoField(primary_key=True)
    name = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="%(class)ss",  # class ImageFolder -> imagefolders
        blank=True,
        null=True,
    )
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
    )

    objects = BaseFolderManager()

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        abstract = True
        unique_together = ("name", "parent")
        ordering = ("tree_id", "lft")

    def __str__(self):
        return self.get_full_path()

    def delete(self, *args, **kwargs):
        if self.file_count():
            raise ValueError("Cannot delete a folder that contains files.")
        super().delete(*args, **kwargs)

    def get_full_path(self):
        return "/".join(
            self.get_ancestors(include_self=True).values_list("name", flat=True)
        )

    def is_deletable(self, user):
        raise NotImplementedError("Subclasses must implement `is_deletable()` method.")

    def is_editable(self, user):
        raise NotImplementedError("Subclasses must implement `is_editable()` method.")

    def is_viewable(self, user):
        raise NotImplementedError("Subclasses must implement `is_viewable()` method.")

    def is_base_folder(self):
        return self.is_root_node()

    def get_base_folder(self):
        return self.get_root()

    def is_children(self, folder):
        return folder.is_descendant_of(self)

    def file_count(self, cumulative=False):
        raise NotImplementedError("Subclasses must implement `files_count()` method.")


class BaseImageManager(models.Manager):
    def deletable(self, user, *, folder=None):
        raise NotImplementedError("Subclasses must implement `deletable()` method.")

    def editable(self, user, *, folder=None):
        raise NotImplementedError("Subclasses must implement `editable()` method.")

    def viewable(self, user, *, folder=None):
        raise NotImplementedError("Subclasses must implement `viewable()` method.")


def get_image_upload_path(instance, filename):
    class_name = instance.__class__.__name__.lower()
    return f"protected/{class_name}s/{filename}"


class AbstractImage(models.Model):
    id = AutoField(primary_key=True)
    name = models.CharField(max_length=250)
    information = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to=get_image_upload_path)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="%(class)ss",  # class Image -> images
        blank=True,
        null=True,
    )

    objects = BaseImageManager()

    class Meta:
        abstract = True
        ordering = ("folder", "name")

    def __str__(self):
        return self.name

    def is_deletable(self, user):
        raise NotImplementedError("Subclasses must implement `is_deletable()` method.")

    def is_editable(self, user):
        raise NotImplementedError("Subclasses must implement `is_editable()` method.")

    def is_viewable(self, user):
        raise NotImplementedError("Subclasses must implement `is_viewable()` method.")
