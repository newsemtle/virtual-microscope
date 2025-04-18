import os
import shutil

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import models
from django.db.models import Q, Value, BooleanField
from django_cte import CTEManager, With
from openslide import OpenSlide
from openslide.deepzoom import DeepZoomGenerator


class FolderManager(CTEManager):
    def user_base_folders(self, user):
        return self.filter(Q(groupprofile__group__in=user.groups.all()))

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
            result = self.none()
            for f in self.user_base_folders(user):
                result |= self.descendants_iter(f)
            return result

        return self.none()

    def viewable(self, user, *, folder=None):
        extra_viewable = self.none()

        if user.is_admin() or user.is_publisher():
            if folder:
                if folder == "root":
                    extra_viewable |= self.filter(parent__isnull=True)
                else:
                    extra_viewable |= self.filter(parent=folder)
            else:
                extra_viewable |= self.all()
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
        descendants = folder.subfolders.all()
        for subfolder in descendants:
            descendants |= self.descendants_iter(subfolder)
        return descendants

    # not used..
    def descendants_cte(self, folder):
        def make_descendants_cte(cte):
            return (
                self.filter(parent_id=folder.id)
                .values("id")
                .union(cte.join(Folder, parent_id=cte.col.id).values("id"), all=True)
            )

        cte = With.recursive(make_descendants_cte)

        descendants = cte.join(Folder, id=cte.col.id).with_cte(cte)

        return descendants


class Folder(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column="created_by",
        related_name="folders",
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

    objects = FolderManager()

    class Meta:
        unique_together = ("name", "parent")
        ordering = ("name",)

    def __str__(self):
        return self.get_full_path()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for slide in self.get_all_slides():
            slide.update_lecture_contents()

    def delete(self, *args, **kwargs):
        if not self.is_empty():
            raise Exception("Folder is not empty. Cannot delete.")
        super().delete(*args, **kwargs)

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()}/{self.name}"
        return self.name

    def is_base_folder(self):
        """Check if this folder is a base folder"""
        return self.parent is None

    def get_base_folder(self):
        """Get the root folder of this folder's hierarchy"""
        current_folder = self
        while current_folder.parent:
            current_folder = current_folder.parent
        return current_folder

    def get_owner_group(self):
        """Get the owner group of this folder"""
        return self.get_base_folder().groupprofile.group

    def is_owner(self, user):
        """Check if the user is the owner of this folder"""
        if user.is_admin():
            return True
        return self.get_owner_group() in user.groups.all()

    def user_can_edit(self, user):
        """Check if the user can edit this folder"""
        if self.is_base_folder():
            return False
        if user.is_admin():
            return True
        return self.is_owner(user)

    def user_can_view(self, user):
        """Check if the user can view this folder"""
        if user.is_admin() or user.is_publisher():
            return True
        return False

    def get_all_slides(self, recursive=False):
        """Get all slides in this folder and its subfolders"""
        slides = list(self.slides.all())
        if recursive:
            for subfolder in self.subfolders.all():
                slides.extend(subfolder.get_all_slides(recursive=True))
        return slides

    def is_empty(self):
        """Check if the folder and the subfolders don't have slides"""
        if self.slides.exists():
            return False
        for subfolder in self.subfolders.all():
            if not subfolder.is_empty():
                return False
        return True

    def is_children(self, folder):
        """Check if the folder is a subfolder of this folder"""
        current_folder = folder.parent
        while current_folder:
            if current_folder == self:
                return True
            current_folder = current_folder.parent
        return False


class SlideManager(models.Manager):
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
            result = self.filter(Q(folder__in=Folder.objects.user_base_folders(user)))
            result |= self.filter(Q(folder__in=Folder.objects.editable(user)))
            return result

        return self.none()

    def viewable(self, user, *, folder=None):
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
                viewable_folders = Folder.objects.viewable(user).filter(
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

        editable = self.editable(user, folder=folder).annotate(
            is_editable=Value(True, BooleanField())
        )
        extra_viewable = extra_viewable.annotate(
            is_editable=Value(False, BooleanField())
        )
        return (editable | extra_viewable).distinct()


class Slide(models.Model):
    class BuildStatus(models.TextChoices):
        PENDING = ("pending", "Pending")
        PROCESSING = ("processing", "Processing")
        DONE = ("done", "Done")
        FAILED = ("failed", "Failed")

    id = models.AutoField(primary_key=True)
    file = models.FileField(
        upload_to="protected/slides/",
        help_text="Choose a slide file to upload.",
    )
    name = models.CharField(
        max_length=250,
        help_text="Name of the slide.",
    )
    information = models.TextField(
        blank=True,
        null=True,
        help_text="Information of the slide.",
    )
    image_root = models.CharField(
        max_length=250,
        blank=True,
        help_text="Relative path to the image directory.",
    )
    metadata = models.JSONField(blank=True, null=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column="created_by",
        related_name="slides",
        blank=True,
        null=True,
    )
    folder = models.ForeignKey(
        "database.Folder",
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
        "database.Slide",
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
