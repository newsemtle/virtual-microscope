import logging
import os
import shutil

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Value, BooleanField, Case, When, Q, F
from mptt.models import MPTTModel
from openslide import OpenSlide
from openslide.deepzoom import DeepZoomGenerator

from apps.common.models import (
    AbstractFolder,
    BaseFolderManager,
    ManagerPermissionMixin,
    ModelPermissionMixin,
)
from apps.lectures.models import Lecture

logger = logging.getLogger("django")


class ImageFolderManager(ManagerPermissionMixin, BaseFolderManager):
    def deletable(self, user, *, parent=None):
        if user.is_admin():
            qs = self.filter(parent__isnull=False)
        elif user.is_publisher():
            qs = self.filter(parent__isnull=False, manager_group__in=user.groups.all())
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
                    condition=Q(
                        parent__isnull=False, manager_group__in=user.groups.all()
                    ),
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
            result = result.filter(groupprofile__group__in=user.groups.all())
        return result


class ImageFolder(ModelPermissionMixin, AbstractFolder):
    manager_group = models.ForeignKey(
        "auth.Group",
        on_delete=models.SET_NULL,
        related_name="managing_imagefolders",
        blank=True,
        null=True,
    )

    objects = ImageFolderManager()

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = self.__class__.objects.get(pk=self.pk)
            if old_instance.manager_group != self.manager_group:
                for slide in self.get_images(cumulative=True):
                    for content in slide.lecture_contents.all():
                        content.handle_non_viewable()

        super().save(*args, **kwargs)

        if not self.is_root_node():
            if self.manager_group != self.parent.manager_group:
                self.manager_group = self.parent.manager_group
                self.__class__.objects.filter(pk=self.pk).update(
                    manager_group=self.manager_group
                )

    def file_count(self, cumulative=False):
        return self.get_images(cumulative=cumulative).count()

    def is_deletable_by(self, user):
        if self.is_root_node():
            return False
        return self.is_managed_by(user)

    def is_editable_by(self, user):
        return self.is_deletable_by(user)

    def is_viewable_by(self, user):
        if self.is_editable_by(user):
            return True

        return user.is_admin() or user.is_publisher()

    def is_managed_by(self, user):
        if user.is_admin():
            return True
        return self.manager_group in user.groups.all()

    def get_images(self, cumulative=False):
        if cumulative:
            return Slide.objects.filter(
                folder__in=self.get_descendants(include_self=True)
            )
        return self.slides.all()


class SlideManager(ManagerPermissionMixin, models.Manager):
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
            qs = self.filter(Q(author=user) | Q(manager_group__in=user.groups.all()))
        else:
            qs = self.none()

        # add filter by folder
        if folder:
            if folder == "root":
                qs = qs.filter(folder__isnull=True)
            else:
                qs = qs.filter(folder=folder)

        return qs.distinct()

    def viewable(self, user, *, folder=None, include_lecture=True):
        if user.is_admin():
            qs = self.all()
        elif user.is_publisher():
            qs = self.filter(
                Q(author=user)
                | Q(manager_group__in=user.groups.all())
                | Q(is_public=True)
            )
        else:
            qs = self.none()

        if include_lecture and (user.is_publisher() or user.is_viewer()):
            qs |= self.filter(
                pk__in=Lecture.objects.viewable(user)
                .values_list("contents__slide", flat=True)
                .distinct()
            )

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
                When(Q(author=user), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
            is_editable = Case(
                When(
                    condition=Q(author=user) | Q(manager_group__in=user.groups.all()),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )

        return qs.distinct().annotate(
            is_deletable=is_deletable, is_editable=is_editable
        )


class Slide(ModelPermissionMixin, models.Model):
    class BuildStatus(models.TextChoices):
        PENDING = ("pending", "Pending")
        PROCESSING = ("processing", "Processing")
        DONE = ("done", "Done")
        FAILED = ("failed", "Failed")

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250)
    information = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="protected/slides/", verbose_name="Image file")
    metadata = models.JSONField(blank=True, null=True)
    image_root = models.CharField(
        max_length=250,
        blank=True,
        help_text="Relative path to the image directory.",
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether the slide is public or not.",
    )
    build_status = models.CharField(
        max_length=10,
        choices=BuildStatus.choices,
        default=BuildStatus.PENDING,
        help_text="Status of the slide processing.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="slides",
        blank=True,
        null=True,
    )
    folder = models.ForeignKey(
        "images.ImageFolder",
        on_delete=models.SET_NULL,
        related_name="slides",
        blank=True,
        null=True,
    )
    manager_group = models.ForeignKey(
        "auth.Group",
        on_delete=models.SET_NULL,
        related_name="managing_images",
        null=True,
        blank=True,
    )

    objects = SlideManager()

    class Meta:
        ordering = ("folder", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        try:
            if self.pk:
                old_instance = self.__class__.objects.get(pk=self.pk)
                if old_instance.file != self.file:
                    self.build_status = self.BuildStatus.PENDING
                    old_instance.file.delete()
                    self._delete_directory(old_instance.get_image_directory())
                if (
                    old_instance.manager_group != self.manager_group
                    or old_instance.is_public != self.is_public
                ):
                    for content in self.lecture_contents.all():
                        content.handle_non_viewable()

            super().save(*args, **kwargs)

            if not self.image_root:
                image_root = os.path.join("protected/processed_images", str(self.id))
                self.__class__.objects.filter(pk=self.pk).update(image_root=image_root)
                self.image_root = image_root

            if self.build_status == self.BuildStatus.PENDING:
                build_slide_task.delay(self.pk)

            if self.folder:
                if self.manager_group != self.folder.manager_group:
                    self.manager_group = self.folder.manager_group
                    self.__class__.objects.filter(pk=self.pk).update(
                        manager_group=self.manager_group
                    )
            else:
                if self.manager_group:
                    self.manager_group = None
                    self.__class__.objects.filter(pk=self.pk).update(manager_group=None)

        except Exception as e:
            raise Exception(f"Failed to save slide: {str(e)}")

    def delete(self, *args, **kwargs):
        try:
            self.file.delete(False)
            self._delete_directory(self.get_image_directory())

            super().delete(*args, **kwargs)

        except Exception as e:
            raise Exception(f"Failed to delete slide: {str(e)}")

    def is_deletable_by(self, user):
        if user.is_admin():
            return True
        return self.author == user

    def is_editable_by(self, user):
        if self.is_deletable_by(user):
            return True

        return self.is_managed_by(user)

    def is_viewable_by(self, user, *, include_lecture=True):
        if self.is_editable_by(user):
            return True

        if user.is_admin():
            return True
        elif user.is_publisher():
            if self.is_public:
                return True

        if include_lecture and (user.is_publisher() or user.is_viewer()):
            return any(
                content.is_viewable_by(user) for content in self.lecture_contents.all()
            )

        return False

    def is_managed_by(self, user):
        if user.is_admin():
            return True
        return self.manager_group in user.groups.all()

    def build_slide(self):
        try:
            self._delete_directory(self.get_image_directory())
            with OpenSlide(self.file.path) as slide:
                self._initialize_slide(slide)
                self._generate_tiles(slide)
        except Exception as e:
            raise Exception(f"Failed to process slide: {str(e)}")

    def get_image_directory(self):
        """Get the path to the image directory"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root)

    def get_dzi_path(self):
        """Get the path to the DZI file"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root, "deepzoom.dzi")

    def get_tile_directory(self):
        """Get the path to the tiles directory"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root, "tiles")

    def get_thumbnail_path(self):
        """Get the URL of the thumbnail image"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root, "thumbnail.png")

    def get_associated_image_path(self):
        """Get the path to the associated image"""
        return os.path.join(
            settings.MEDIA_ROOT, self.image_root, "associated_image.png"
        )

    def building(self):
        if self.build_status == self.BuildStatus.PENDING:
            return True
        if self.build_status == self.BuildStatus.PROCESSING:
            return True
        return False

    def _initialize_slide(self, slide: OpenSlide):
        channel_layer = get_channel_layer()
        try:
            async_to_sync(channel_layer.group_send)(
                f"slide_{self.pk}",
                {
                    "type": "slide.initialize",
                    "completed": False,
                    "status": "Initializing slide",
                },
            )

            # Setup directory
            image_directory = self.get_image_directory()
            os.makedirs(image_directory, exist_ok=True)

            # Save thumbnail
            thumbnail_size = (256, 256)
            thumbnail = slide.get_thumbnail(thumbnail_size)
            thumbnail.resize(thumbnail_size).save(self.get_thumbnail_path())

            # Save associated image
            slide.associated_images.get("macro").save(self.get_associated_image_path())

            # Save metadata
            full_metadata = slide.properties
            metadata = {
                "mpp-x": float(full_metadata.get("openslide.mpp-x")),
                "mpp-y": float(full_metadata.get("openslide.mpp-y")),
                "sourceLens": int(full_metadata.get("hamamatsu.SourceLens")),
                "created": full_metadata.get("hamamatsu.Created"),
            }
            self.__class__.objects.filter(pk=self.pk).update(metadata=metadata)
            self.metadata = metadata

            async_to_sync(channel_layer.group_send)(
                f"slide_{self.pk}",
                {
                    "type": "slide.initialize",
                    "completed": True,
                    "status": "Slide initialized",
                },
            )

        except Exception as e:
            raise Exception(f"Failed to setup slide: {str(e)}")

    def _generate_tiles(self, slide: OpenSlide):
        """Generate related images for the slide"""

        tile_format = "jpeg"  # jpeg or png

        channel_layer = get_channel_layer()

        try:
            # Setup directory
            tile_directory = self.get_tile_directory()
            os.makedirs(tile_directory, exist_ok=True)

            deepzoom = DeepZoomGenerator(slide)

            async_to_sync(channel_layer.group_send)(
                f"slide_{self.pk}",
                {
                    "type": "progress.update",
                    "progress": 5,
                    "status": "Creating DZI file",
                },
            )
            # Create DZI file
            dzi = deepzoom.get_dzi(tile_format)
            with open(self.get_dzi_path(), "w") as f:
                f.write(dzi)

            # Get the total number of tiles
            total_tiles = sum(cols * rows for cols, rows in deepzoom.level_tiles)
            processed_tiles = 0
            batch_size = 10

            # Generate tiles
            for level in range(deepzoom.level_count):
                level_dir = os.path.join(tile_directory, str(level))
                os.makedirs(level_dir, exist_ok=True)

                cols, rows = deepzoom.level_tiles[level]
                for col in range(cols):
                    for row in range(rows):
                        if processed_tiles % batch_size == 0:
                            progress = 5 + int((processed_tiles / total_tiles) * 90)
                            async_to_sync(channel_layer.group_send)(
                                f"slide_{self.pk}",
                                {
                                    "type": "progress.update",
                                    "progress": progress,
                                    "status": f"Processing tiles ({processed_tiles}/{total_tiles})",
                                },
                            )

                        tile_path = os.path.join(
                            level_dir, f"{col}_{row}.{tile_format}"
                        )
                        tile = deepzoom.get_tile(level, (col, row))
                        tile.save(tile_path)
                        processed_tiles += 1

            async_to_sync(channel_layer.group_send)(
                f"slide_{self.pk}",
                {
                    "type": "progress.update",
                    "progress": 100,
                    "status": "Tile generation complete",
                },
            )

        except Exception as e:
            async_to_sync(channel_layer.group_send)(
                f"slide_{self.pk}",
                {
                    "type": "progress.update",
                    "progress": -1,
                    "status": f"Error: {str(e)}",
                },
            )
            raise Exception(f"Failed to generate images: {str(e)}")

    @staticmethod
    def _delete_directory(image_directory):
        try:
            if os.path.exists(image_directory):
                shutil.rmtree(image_directory)
        except Exception as e:
            raise Exception(f"Failed to delete image directory: {str(e)}")


class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    slides = models.ManyToManyField(
        "images.Slide",
        related_name="tags",
        blank=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tags",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ("name",)

    def __str__(self):
        return self.name


@shared_task
def build_slide_task(slide_id):
    try:
        slide = Slide.objects.get(pk=slide_id)
        slide.build_status = slide.BuildStatus.PROCESSING
        slide.save(update_fields=["build_status"])
        slide.build_slide()
        slide.build_status = Slide.BuildStatus.DONE
        slide.save(update_fields=["build_status"])
    except Exception as e:
        try:
            slide = Slide.objects.get(pk=slide_id)
            slide.build_status = Slide.BuildStatus.FAILED
            slide.save(update_fields=["build_status"])
            raise Exception(f"Failed to process slide {slide_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to process slide {slide_id}: {str(e)}")
