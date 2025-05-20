import logging
import os
import shutil
from datetime import datetime

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Value, BooleanField, Case, When, Q, F
from django.utils.translation import gettext as _, gettext_lazy as _lazy, pgettext_lazy
from mptt.models import MPTTModel
from openslide import OpenSlide
from openslide.deepzoom import DeepZoomGenerator

from apps.core.models import (
    AbstractFolder,
    BaseFolderManager,
    ManagerPermissionMixin,
    ModelPermissionMixin,
)
from apps.lectures.models import Lecture, LectureContent

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
        verbose_name=_lazy("manager group"),
        on_delete=models.SET_NULL,
        related_name="managing_imagefolders",
        blank=True,
        null=True,
    )

    objects = ImageFolderManager()

    def save(self, *args, **kwargs):
        handle_manager_group = False

        # manager group
        if not self.is_root_node() and self.manager_group != self.parent.manager_group:
            self.manager_group = self.parent.manager_group

        if self.pk:
            old = self.__class__.objects.get(pk=self.pk)

            handle_manager_group = self.manager_group != old.manager_group

        super().save(*args, **kwargs)

        if handle_manager_group:
            self._update_descendants_and_images_manager_group()

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

    def _update_descendants_and_images_manager_group(self):
        descendants = self.get_descendants(include_self=True)
        descendants.update(manager_group=self.manager_group)

        slides = (
            Slide.objects.filter(folder__in=descendants)
            .select_related("manager_group")
            .only("id", "manager_group_id")
        )
        slides.update(manager_group=self.manager_group)
        # reduce the memory load by using iterator to disable caching
        for slide in slides.iterator():
            LectureContent.objects.handle_unavailable_by_slide(slide)


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
        PENDING = ("pending", _lazy("Pending"))
        PROCESSING = ("processing", _lazy("Processing"))
        DONE = ("done", _lazy("Done"))
        FAILED = ("failed", _lazy("Failed"))

    ALLOWED_EXTENSIONS = ["ndpi", "svs"]
    TILE_FORMAT = "jpeg"  # jpeg or png

    id = models.AutoField(primary_key=True)
    name = models.CharField(_lazy("name"), max_length=250)
    information = models.TextField(_lazy("information"), blank=True, null=True)
    file = models.FileField(
        _lazy("file"),
        upload_to="protected/slides/",
        validators=[FileExtensionValidator(ALLOWED_EXTENSIONS)],
    )
    metadata = models.JSONField(_lazy("metadata"), blank=True, null=True)
    image_root = models.CharField(
        _lazy("image root"),
        max_length=250,
        blank=True,
        help_text=_lazy("Relative path to the image directory."),
    )
    is_public = models.BooleanField(
        _lazy("public"),
        default=False,
        help_text=_lazy("Whether the slide is public or private (manager group)."),
    )
    build_status = models.CharField(
        _lazy("build status"),
        max_length=10,
        choices=BuildStatus.choices,
        default=BuildStatus.PENDING,
        help_text=_lazy("Status of the slide processing."),
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
        related_name="slides",
        blank=True,
        null=True,
    )
    folder = models.ForeignKey(
        "images.ImageFolder",
        verbose_name=_lazy("folder"),
        on_delete=models.SET_NULL,
        related_name="slides",
        blank=True,
        null=True,
    )
    manager_group = models.ForeignKey(
        "auth.Group",
        verbose_name=_lazy("manager group"),
        on_delete=models.SET_NULL,
        related_name="managing_images",
        null=True,
        blank=True,
    )

    objects = SlideManager()

    class Meta:
        verbose_name = _lazy("slide")
        verbose_name_plural = _lazy("slides")
        ordering = ("folder", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        handle_manager_group = False

        # image root
        if not self.image_root:
            self.image_root = os.path.join("protected/processed_images", str(self.id))

        # manager group
        if self.folder and self.manager_group != self.folder.manager_group:
            self.manager_group = self.folder.manager_group
        elif not self.folder and self.manager_group:
            self.manager_group = None

        if self.pk:
            old = self.__class__.objects.get(pk=self.pk)

            # file
            if self.file != old.file:
                old.file.delete()
                self._delete_directory(old.image_directory_path)
                self.build_status = self.BuildStatus.PENDING

            handle_manager_group = (
                self.manager_group != old.manager_group
                or self.is_public != old.is_public
            )

        super().save(*args, **kwargs)

        # build
        if self.build_status == self.BuildStatus.PENDING:
            build_slide_task.delay(self.pk)

        if handle_manager_group:
            LectureContent.objects.handle_unavailable_by_slide(self)

    def delete(self, *args, **kwargs):
        try:
            self.file.delete(False)
            self._delete_directory(self.image_directory_path)

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

    def building(self):
        if self.build_status == self.BuildStatus.PENDING:
            return True
        if self.build_status == self.BuildStatus.PROCESSING:
            return True
        return False

    def run_build_process(self):
        try:
            self.__class__.objects.filter(pk=self.pk).update(
                build_status=self.BuildStatus.PROCESSING
            )

            # process
            self._delete_directory(self.image_directory_path)
            with OpenSlide(self.file.path) as slide:
                self._initialize_slide(slide)
                self._generate_tiles(slide)

            self.__class__.objects.filter(pk=self.pk).update(
                build_status=self.BuildStatus.DONE
            )
        except Exception as e:
            self.__class__.objects.filter(pk=self.pk).update(
                build_status=self.BuildStatus.FAILED
            )
            logger.error(f"Failed to build slide {self.pk}: {e}")

    @property
    def file_name(self):
        """Get the name of the file"""
        return os.path.basename(self.file.name)

    @property
    def file_extension(self):
        """Get the extension of the file"""
        _, extension = os.path.splitext(self.file.name)
        return extension.lower()[1:]

    @property
    def image_directory_path(self):
        """Get the path to the image directory"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root)

    @property
    def tile_directory_path(self):
        """Get the path to the tile directory"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root, "tiles")

    @property
    def associated_image_directory_path(self):
        """Get the path to the associated image directory"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root, "associated_images")

    @property
    def associated_image_names(self):
        """Get the names of the associated images"""
        return os.listdir(self.associated_image_directory_path)

    @property
    def dzi_path(self):
        """Get the path to the DZI file"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root, "deepzoom.dzi")

    @property
    def thumbnail_path(self):
        """Get the URL of the thumbnail image"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root, "thumbnail.png")

    def _initialize_slide(self, slide: OpenSlide):
        channel_layer = get_channel_layer()
        try:
            async_to_sync(channel_layer.group_send)(
                f"slide_{self.pk}",
                {
                    "type": "slide.initialize",
                    "completed": False,
                    "status": _("Initializing slide"),
                },
            )

            # Setup directory
            image_directory = self.image_directory_path
            associated_image_directory = self.associated_image_directory_path
            os.makedirs(image_directory, exist_ok=True)
            os.makedirs(associated_image_directory, exist_ok=True)

            # Save thumbnail
            thumbnail_size = (256, 256)
            thumbnail = slide.get_thumbnail(thumbnail_size)
            thumbnail.resize(thumbnail_size).save(self.thumbnail_path)

            # Save associated images
            for name, image in slide.associated_images.items():
                image_path = os.path.join(associated_image_directory, f"{name}.png")
                image.save(image_path)

            # Save metadata
            full_metadata = slide.properties
            metadata = {
                "mpp-x": float(full_metadata.get("openslide.mpp-x")),
                "mpp-y": float(full_metadata.get("openslide.mpp-y")),
                "objective_power": int(full_metadata.get("openslide.objective-power")),
                "vendor": full_metadata.get("openslide.vendor"),
                "created": self._get_format_specific_metadata(
                    full_metadata, self.file_extension
                ),
            }
            self.__class__.objects.filter(pk=self.pk).update(metadata=metadata)
            self.metadata = metadata

            async_to_sync(channel_layer.group_send)(
                f"slide_{self.pk}",
                {
                    "type": "slide.initialize",
                    "completed": True,
                    "status": _("Slide initialized"),
                },
            )

        except Exception as e:
            raise Exception(f"Failed to setup slide: {str(e)}")

    def _generate_tiles(self, slide: OpenSlide):
        channel_layer = get_channel_layer()

        try:
            # Setup directory
            tile_directory = self.tile_directory_path
            os.makedirs(tile_directory, exist_ok=True)

            deepzoom = DeepZoomGenerator(slide)

            async_to_sync(channel_layer.group_send)(
                f"slide_{self.pk}",
                {
                    "type": "progress.update",
                    "progress": 5,
                    "status": _("Creating DZI file"),
                },
            )
            # Create DZI file
            dzi = deepzoom.get_dzi(Slide.TILE_FORMAT)
            with open(self.dzi_path, "w") as f:
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
                                    "status": _("Processing tiles")
                                    + f" ({processed_tiles}/{total_tiles})",
                                },
                            )

                        tile_path = os.path.join(
                            level_dir, f"{col}_{row}.{Slide.TILE_FORMAT}"
                        )
                        tile = deepzoom.get_tile(level, (col, row))
                        tile.save(tile_path)
                        processed_tiles += 1

            async_to_sync(channel_layer.group_send)(
                f"slide_{self.pk}",
                {
                    "type": "progress.update",
                    "progress": 100,
                    "status": _("Tile generation complete"),
                },
            )

        except Exception as e:
            async_to_sync(channel_layer.group_send)(
                f"slide_{self.pk}",
                {
                    "type": "progress.update",
                    "progress": -1,
                    "status": _("Failed to generate tiles"),
                },
            )
            logger.error(f"Failed to generate tiles for slide {self.pk}: {str(e)}")

    @staticmethod
    def _delete_directory(image_directory):
        try:
            if os.path.exists(image_directory):
                shutil.rmtree(image_directory)
        except Exception as e:
            logger.error(
                f"Failed to delete image directory '{image_directory}': {str(e)}"
            )

    @staticmethod
    def _get_format_specific_metadata(full_metadata, vendor_name):
        vendor_name = vendor_name.lower()
        if vendor_name == "ndpi":
            created_raw = full_metadata.get("hamamatsu.Created")
            if created_raw:
                try:
                    return datetime.strptime(created_raw, "%Y/%m/%d").strftime(
                        "%Y-%m-%d"
                    )
                except ValueError:
                    return created_raw
            else:
                return None
        elif vendor_name == "svs":
            created_raw = full_metadata.get("aperio.Date")
            if created_raw:
                try:
                    return datetime.strptime(created_raw, "%m/%d/%y").strftime(
                        "%Y-%m-%d"
                    )
                except ValueError:
                    return created_raw
            else:
                return None
        else:
            return None


class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(_lazy("name"), max_length=100)
    created_at = models.DateTimeField(
        pgettext_lazy("date", "created"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        pgettext_lazy("date", "updated"),
        auto_now=True,
    )

    slides = models.ManyToManyField(
        "images.Slide",
        verbose_name=_lazy("slides"),
        related_name="tags",
        blank=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_lazy("author"),
        on_delete=models.CASCADE,
        related_name="tags",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _lazy("Tag")
        verbose_name_plural = _lazy("Tags")
        unique_together = ("name", "author")
        ordering = ("name",)

    def __str__(self):
        return self.name


@shared_task
def build_slide_task(slide_id):
    try:
        slide = Slide.objects.get(pk=slide_id)
        slide.run_build_process()
    except Slide.DoesNotExist:
        logger.error(f"Slide {slide_id} does not exist.")
