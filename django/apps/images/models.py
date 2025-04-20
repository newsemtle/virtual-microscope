import os
import shutil

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import models
from django.db.models import Q, Value, BooleanField, Case, When
from mptt.models import MPTTModel
from openslide import OpenSlide
from openslide.deepzoom import DeepZoomGenerator

from apps.common.models import (
    AbstractFolder,
    BaseFolderManager,
    AbstractImage,
    BaseImageManager,
)


class ImageFolderManager(BaseFolderManager):
    def user_base_folders(self, user):
        return self.filter(Q(groupprofile__group__in=user.groups.all()))

    def editable(self, user, *, folder=None):
        if folder == "root":
            return self.none()

        if user.is_admin():
            return (
                self.filter(parent=folder)
                if folder
                else self.filter(parent__isnull=False)
            )

        if user.is_publisher():
            if folder:
                return (
                    self.filter(parent=folder) if folder.is_owner(user) else self.none()
                )
            result = self.none()
            for f in self.user_base_folders(user):
                result |= f.get_descendants()
            return result

        return self.none()

    def viewable(self, user, *, folder=None):
        if not (user.is_admin() or user.is_publisher()):
            return self.none()

        editable = self.editable(user, folder=folder)
        extra_viewable = self.none()

        if folder:
            if folder == "root":
                extra_viewable |= self.filter(parent__isnull=True)
            else:
                extra_viewable |= self.filter(parent=folder)
        else:
            extra_viewable |= self.all()

        viewable = (
            (editable | extra_viewable)
            .distinct()
            .annotate(
                is_editable=Case(
                    When(pk__in=editable.values("pk"), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            )
        )

        return viewable


class ImageFolder(AbstractFolder):
    objects = ImageFolderManager()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for slide in self.get_all_images():
            slide.update_lecture_contents()

    def get_owner_group(self):
        return self.get_base_folder().groupprofile.group

    def is_owner(self, user):
        if user.is_admin():
            return True
        return self.get_owner_group() in user.groups.all()

    def user_can_edit(self, user):
        if self.is_base_folder():
            return False
        if user.is_admin():
            return True
        return self.is_owner(user)

    def user_can_view(self, user):
        return user.is_admin() or user.is_publisher()

    def get_all_images(self, cumulative=False):
        if cumulative:
            return self.get_descendants(include_self=True).values_list(
                "slides", flat=True
            )
        return self.slides.all()

    def file_count(self, cumulative=False):
        return self.get_all_images(cumulative=cumulative).count()


class SlideManager(BaseImageManager):
    def editable(self, user, *, folder=None):
        if user.is_admin():
            if folder:
                if folder == "root":
                    return self.filter(folder__isnull=True)
                return self.filter(folder=folder)
            return self.all()
        elif user.is_publisher():
            if folder:
                if folder == "root" or not folder.is_owner(user):
                    return self.none()
                return self.filter(folder=folder)
            result = self.filter(
                Q(folder__in=ImageFolder.objects.user_base_folders(user))
            )
            result |= self.filter(Q(folder__in=ImageFolder.objects.editable(user)))
            return result

        return self.none()

    def viewable(self, user, *, folder=None):
        editable = self.editable(user, folder=folder)
        extra_viewable = self.none()

        if user.is_publisher():
            if folder:
                if folder == "root":
                    extra_viewable |= self.filter(
                        Q(folder__isnull=True) & Q(is_public=True)
                    )
                elif not folder.is_owner(user):
                    extra_viewable |= self.filter(Q(folder=folder) & Q(is_public=True))
            else:
                extra_viewable |= self.filter(
                    Q(folder__isnull=True) & Q(is_public=True)
                )
                viewable_folders = ImageFolder.objects.viewable(user).filter(
                    is_editable=False
                )
                extra_viewable |= self.filter(
                    Q(folder__in=viewable_folders) & Q(is_public=True)
                )

        if not folder:
            lecture_slides = self.none()
            for group in user.groups.all():
                for lecture in group.lectures.filter(is_active=True):
                    lecture_slides |= lecture.get_slides()
            extra_viewable |= lecture_slides

        viewable = (
            (editable | extra_viewable)
            .distinct()
            .annotate(
                is_editable=Case(
                    When(pk__in=editable.values("pk"), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            )
        )

        return viewable


class Slide(AbstractImage):
    class BuildStatus(models.TextChoices):
        PENDING = ("pending", "Pending")
        PROCESSING = ("processing", "Processing")
        DONE = ("done", "Done")
        FAILED = ("failed", "Failed")

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
        choices=BuildStatus,
        default=BuildStatus.PENDING,
        help_text="Status of the slide processing.",
    )

    folder = models.ForeignKey(
        "images.ImageFolder",
        on_delete=models.SET_NULL,
        related_name="slides",
        blank=True,
        null=True,
    )

    objects = SlideManager()

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        try:
            if self.pk:
                old_instance = Slide.objects.get(pk=self.pk)
                if old_instance.file != self.file:
                    self.build_status = self.BuildStatus.PENDING
                    old_instance.file.delete()
                    self._delete_directory(old_instance.get_image_directory())
                if (
                    old_instance.folder != self.folder
                    or old_instance.is_public != self.is_public
                ):
                    self.update_lecture_contents()

            super().save(*args, **kwargs)

            if not self.image_root:
                image_root = os.path.join("protected/processed_images", str(self.id))
                Slide.objects.filter(pk=self.pk).update(image_root=image_root)
                self.image_root = image_root

            if self.build_status == self.BuildStatus.PENDING:
                build_slide_task.delay(self.pk)

        except Exception as e:
            raise Exception(f"Failed to save slide: {str(e)}")

    def delete(self, *args, **kwargs):
        try:
            self.file.delete(False)
            self._delete_directory(self.get_image_directory())

            super().delete(*args, **kwargs)

        except Exception as e:
            raise Exception(f"Failed to delete slide: {str(e)}")

    def build_slide(self):
        try:
            self._delete_directory(self.get_image_directory())
            with OpenSlide(self.file.path) as slide:
                self._initialize_slide(slide)
                self._generate_tiles(slide)
        except Exception as e:
            raise Exception(f"Failed to process slide: {str(e)}")

    def update_lecture_contents(self):
        for lecture_content in self.lecture_contents.all():
            lecture_content.update()

    def get_owner_group(self):
        """Get the group of this slide"""
        if self.folder:
            return self.folder.get_owner_group()
        return None

    def user_can_edit(self, user):
        """Check if the user can edit the slide"""
        if user.is_admin():
            return True
        if self.folder:
            return self.folder.is_owner(user)
        return False

    def user_can_view(self, user):
        """Check if the user can view the slide"""
        if user.is_admin():
            return True
        if user.is_publisher():
            if self.user_can_edit(user) or self.is_public:
                return True
        if user.is_viewer():
            for content in self.lecture_contents.all():
                if content.user_can_view(user):
                    return True
        return False

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
            Slide.objects.filter(pk=self.pk).update(metadata=metadata)
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

            # Get total number of tiles
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
    created_by = models.ForeignKey(
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
        except Slide.DoesNotExist:
            return
