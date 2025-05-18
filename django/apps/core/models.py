from django.conf import settings
from django.db import models
from django.db.models import AutoField
from django.utils.translation import gettext_lazy as _lazy, pgettext_lazy
from mptt.managers import TreeManager
from mptt.models import MPTTModel, TreeForeignKey


class ManagerPermissionMixin:
    def deletable(self, user):
        raise NotImplementedError("Subclasses must implement `deletable()` method.")

    def editable(self, user):
        raise NotImplementedError("Subclasses must implement `editable()` method.")

    def viewable(self, user):
        raise NotImplementedError("Subclasses must implement `viewable()` method.")


class ModelPermissionMixin:
    def is_deletable_by(self, user):
        raise NotImplementedError(
            "Subclasses must implement `is_deletable_by()` method."
        )

    def is_editable_by(self, user):
        raise NotImplementedError(
            "Subclasses must implement `is_editable_by()` method."
        )

    def is_viewable_by(self, user):
        raise NotImplementedError(
            "Subclasses must implement `is_viewable_by()` method."
        )


class BaseFolderManager(TreeManager):
    pass


class AbstractFolder(MPTTModel):
    id = AutoField(primary_key=True)
    name = models.CharField(_lazy("name"), max_length=250)
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
        related_name="%(class)ss",  # e.g., class ImageFolder -> imagefolders
        blank=True,
        null=True,
    )
    parent = TreeForeignKey(
        "self",
        verbose_name=pgettext_lazy("folder", "parent"),
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
        verbose_name = _lazy("folder")
        verbose_name_plural = _lazy("folders")
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

    def file_count(self, cumulative=False):
        raise NotImplementedError("Subclasses must implement `file_count()` method.")
