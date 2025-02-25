import os
import shutil

from django.conf import settings
from django.db import models
from openslide import OpenSlide
from openslide.deepzoom import DeepZoomGenerator


class FolderManager(models.Manager):
    def base_folders(self):
        return self.filter(parent__isnull=True)

    def editable_base_folders(self, user):
        if user.is_admin():
            return self.base_folders()
        return self.base_folders().filter(groupprofile__group__in=user.groups.all())

    def editable(self, user):
        if user.is_admin():
            return self.all()
        folders = self.editable_base_folders(user)
        for folder in self.editable_base_folders(user):
            folders |= self.descendents(folder)
        return folders

    def viewable(self, user):
        return self.all()

    def descendents(self, folder):
        folders = folder.subfolders.all()
        for subfolder in folder.subfolders.all():
            folders |= self.descendents(subfolder)
        return folders


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
            slide.update_lectures()

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

    def get_group(self):
        """Get the group of this folder"""
        return self.get_base_folder().groupprofile.group

    def user_can_edit(self, user):
        """Check if the user can edit this folder"""
        if user.is_admin():
            return True
        return self.get_group() in user.groups.all()

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
    def root_slides(self):
        """Get slides that aren't in any folder"""
        return self.filter(folder__isnull=True)

    def viewable_by_folder(self, user, folder):
        """Get slides by folder that are accessible to the user"""
        if not folder:
            if user.is_admin():
                return self.filter(folder__isnull=True)
            else:
                return self.filter(folder__isnull=True, is_public=True)
        elif folder.user_can_edit(user):
            return self.filter(folder=folder)
        else:
            return self.filter(folder=folder, is_public=True)

    def editable(self, user):
        """Get slides that are accessible to the user"""
        if user.is_admin():
            return self.all()
        slides = self.none()
        for folder in Folder.objects.editable(user):
            slides |= folder.slides
        return slides

    def viewable(self, user):
        """Get slides that are accessible to the user"""
        if user.is_admin():
            return self.all()
        slides = self.root_slides().filter(is_public=True)
        for folder in Folder.objects.viewable(user):
            slides |= self.viewable_by_folder(user, folder)
        return slides


class Slide(models.Model):
    id = models.AutoField(primary_key=True)
    file = models.FileField(
        upload_to="slides/",
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
            need_slide_processing = True
            if self.pk:
                old_instance = Slide.objects.get(pk=self.pk)
                if old_instance.file != self.file:
                    # delete old slide file
                    old_instance.file.delete()
                    # delete old image directory
                    self._delete_directory(old_instance.get_image_directory())
                else:
                    need_slide_processing = False

            super().save(*args, **kwargs)

            if not self.image_root:
                image_root = os.path.join("images", str(self.id))
                Slide.objects.filter(pk=self.pk).update(image_root=image_root)
                self.image_root = image_root

            if need_slide_processing:
                self.process_slide()

            self.update_lectures()

        except Exception as e:
            raise Exception(f"Failed to save slide: {str(e)}")

    def delete(self, *args, **kwargs):
        try:
            self.file.delete(False)
            self._delete_directory(self.get_image_directory())
            super().delete(*args, **kwargs)
        except Exception as e:
            raise Exception(f"Failed to delete slide: {str(e)}")

    def process_slide(self):
        try:
            with OpenSlide(self.file.path) as slide:
                self._generate_images(slide)
                self._save_metadata(slide)
        except Exception as e:
            raise Exception(f"Failed to process slide: {str(e)}")

    def check_integrity(self):
        """Check integrity of the slide's files and metadata"""

        status = {
            "needs_repair": False,
            "file_exists": os.path.exists(self.file.path),
            "dzi_exists": os.path.exists(self.get_dzi_path()),
            "tiles_complete": False,
            "thumbnail_exists": False,
            "associated_image_exists": False,
            "metadata_valid": False,
        }

        # Check tiles
        try:
            with OpenSlide(self.file.path) as slide:
                deepzoom = DeepZoomGenerator(slide)
                status["tiles_complete"] = self._verify_tiles(deepzoom)
        except:
            status["tiles_complete"] = False

        status["thumbnail_exists"] = os.path.exists(self.get_thumbnail_path())
        status["associated_image_exists"] = os.path.exists(
            self.get_associated_image_path()
        )
        status["metadata_valid"] = self._verify_metadata()

        status["needs_repair"] = not all(
            [
                status["file_exists"],
                status["dzi_exists"],
                status["tiles_complete"],
                status["thumbnail_exists"],
                status["associated_image_exists"],
                status["metadata_valid"],
            ]
        )

        return status

    def repair(self, status):
        """Repair any missing or corrupted components"""

        status = self.check_integrity()

        if not status["needs_repair"]:
            return status

        if not status["file_exists"]:
            raise Exception("Original slide file does not exist")

        try:
            with OpenSlide(self.file.path) as slide:
                image_directory = self.get_image_directory()

                if not (
                    status["dzi_exists"]
                    and status["tiles_complete"]
                    and status["thumbnail_exists"]
                    and status["associated_image_exists"]
                ):
                    self._delete_directory(image_directory)
                    self._generate_images(slide)

                if not status["metadata_valid"]:
                    self._save_metadata(slide)

            return self.check_integrity()

        except Exception as e:
            raise Exception(
                f"Failed to repair slide {self.name} (id={self.id}): {str(e)}"
            )

    def update_lectures(self):
        for lecture_content in self.lecture_contents.all():
            if not self.user_can_view(lecture_content.lecture.author):
                lecture_content.delete()

    def get_group(self):
        """Get the group of this slide"""
        if self.folder:
            return self.folder.get_group()
        return None

    def user_can_edit(self, user):
        """Check if the user can edit the slide"""
        if user.is_admin():
            return True
        elif self.folder:
            return self.folder.user_can_edit(user)
        return False

    def user_can_view(self, user):
        """Check if the user can view the slide"""
        return self.is_public or self.user_can_edit(user)

    def get_image_directory(self):
        """Get the path to the image directory"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root)

    def get_dzi_path(self):
        """Get the path to the DZI file"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root, "image.dzi")

    def get_tile_directory(self):
        """Get the path to the tiles directory"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root, "image_files")

    def get_thumbnail_path(self):
        """Get the URL of the thumbnail image"""
        return os.path.join(settings.MEDIA_ROOT, self.image_root, "thumbnail.png")

    def get_associated_image_path(self):
        """Get the path to the associated image"""
        return os.path.join(
            settings.MEDIA_ROOT, self.image_root, "associated_image.png"
        )

    def _generate_images(self, slide: OpenSlide):
        """Generate related images for the slide"""

        tile_format = "jpeg"  # jpeg or png

        try:
            # Setup directory
            tile_directory = self.get_tile_directory()
            os.makedirs(tile_directory, exist_ok=True)

            deepzoom = DeepZoomGenerator(slide)

            # Create DZI file
            dzi = deepzoom.get_dzi(tile_format)
            with open(self.get_dzi_path(), "w") as f:
                f.write(dzi)

            # Generate tiles
            for level in range(deepzoom.level_count):
                level_dir = os.path.join(tile_directory, str(level))
                os.makedirs(level_dir, exist_ok=True)

                cols, rows = deepzoom.level_tiles[level]
                for col in range(cols):
                    for row in range(rows):
                        tile_path = os.path.join(
                            level_dir, f"{col}_{row}.{tile_format}"
                        )
                        tile = deepzoom.get_tile(level, (col, row))
                        tile.save(tile_path)

            # Save thumbnail and associated image
            thumbnail_size = (256, 256)
            thumbnail = slide.get_thumbnail(thumbnail_size)
            thumbnail.resize(thumbnail_size).save(self.get_thumbnail_path())
            slide.associated_images.get("macro").save(self.get_associated_image_path())

        except Exception as e:
            raise Exception(f"Failed to generate images: {str(e)}")

    def _save_metadata(self, slide):
        """Extract and save metadata from the slide"""

        try:
            full_metadata = slide.properties
            metadata = {
                "mpp-x": float(full_metadata.get("openslide.mpp-x")),
                "mpp-y": float(full_metadata.get("openslide.mpp-y")),
                "sourceLens": int(full_metadata.get("hamamatsu.SourceLens")),
                "created": full_metadata.get("hamamatsu.Created"),
            }
            Slide.objects.filter(pk=self.pk).update(metadata=metadata)
            self.metadata = metadata  # Update instance attribute
        except Exception as e:
            raise Exception(f"Failed to save metadata: {str(e)}")

    def _verify_tiles(self, deepzoom):
        """Verify all expected tiles exist"""

        for level in range(deepzoom.level_count):
            level_dir = os.path.join(self.get_tile_directory(), str(level))
            if not os.path.exists(level_dir):
                return False

            cols, rows = deepzoom.level_tiles[level]
            expected_tiles = set(
                f"{col}_{row}.jpeg" for col in range(cols) for row in range(rows)
            )
            existing_tiles = set(os.listdir(level_dir))
            if not expected_tiles.issubset(existing_tiles):
                return False

        return True

    def _verify_metadata(self):
        """Verify metadata is complete"""

        if not self.metadata:
            return False

        required_fields = {"mpp-x", "mpp-y", "sourceLens", "created"}
        return required_fields.issubset(self.metadata.keys())

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
    slides = models.ManyToManyField(
        "database.Slide",
        related_name="tags",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
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
