import logging
import re

from PIL import Image
from django.contrib.auth import user_logged_out
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
    Permission,
    Group,
)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext as _, gettext_lazy as _lazy

from apps.images.models import ImageFolder
from apps.lectures.models import LectureFolder, LectureContent

logger = logging.getLogger("django")


@receiver(post_save, sender=Group)
def update_group_profile(sender, instance, created, **kwargs):
    try:
        profile = instance.profile
        if not profile.base_image_folder and profile.is_publisher_type():
            profile.create_base_image_folder()
        elif (
            profile.base_image_folder
            and profile.base_image_folder.name != instance.name.title()
        ):
            profile.base_image_folder.name = instance.name.title()
            profile.base_image_folder.save(update_fields=["name"])

    except ObjectDoesNotExist:
        GroupProfile.objects.create(group=instance)


@receiver(pre_delete, sender=Group)
def on_delete_group_profile(sender, instance, **kwargs):
    profile = instance.profile

    try:
        if profile.base_image_folder:
            profile.base_image_folder.delete()
    except ValidationError as e:
        logger.error(f"Failed to delete base image folder: {str(e)}")

    profile.delete()


class GroupProfile(models.Model):
    class Type(models.TextChoices):
        PUBLISHER = ("1", _lazy("Publisher"))
        VIEWER = ("2", _lazy("Viewer"))

    id = models.AutoField(primary_key=True)
    type = models.CharField(
        _lazy("type"),
        max_length=10,
        choices=Type.choices,
        default=Type.VIEWER,
        blank=False,
        help_text=_lazy("Type of the group."),
    )

    group = models.OneToOneField(
        "auth.Group",
        verbose_name=_lazy("group"),
        on_delete=models.SET_NULL,
        related_name="profile",
        blank=True,
        null=True,
    )
    base_image_folder = models.OneToOneField(
        "images.ImageFolder",
        verbose_name=_lazy("base image folder"),
        on_delete=models.SET_NULL,
        related_name="groupprofile",
        blank=True,
        null=True,
        help_text=_lazy("Base image folder for the publisher group."),
    )

    def __str__(self):
        return _("Profile for '{group_name}' group").format(group_name=self.group.name)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.set_default_permission()

    def set_default_permission(self):
        self.group.permissions.clear()
        if self.is_publisher_type():
            q = Q(content_type__app_label="images")
            q |= Q(content_type__app_label="lectures")
            q |= Q(content_type__model="annotation")
            self.group.permissions.set(Permission.objects.filter(q))
        elif self.is_viewer_type():
            q = Q(content_type__model="slide", codename__contains="view")
            q |= Q(content_type__model="lecture", codename__contains="view")
            q |= Q(content_type__model="lecturecontent", codename__contains="view")
            q |= Q(content_type__model="annotation", codename__contains="view")
            self.group.permissions.set(Permission.objects.filter(q))

    def is_publisher_type(self):
        return self.type == self.Type.PUBLISHER

    def is_viewer_type(self):
        return self.type == self.Type.VIEWER

    def create_base_image_folder(self):
        self.base_image_folder = ImageFolder.objects.create(
            name=self.group.name.title(),
            author=User.objects.filter(is_superuser=True).first(),
            manager_group=self.group,
        )
        self.__class__.objects.filter(pk=self.pk).update(
            base_image_folder=self.base_image_folder
        )


class UserManager(BaseUserManager):
    def create_user(
        self, username, first_name, last_name, password=None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(
            username, first_name, last_name, password, **extra_fields
        )

    def create_superuser(
        self, username, first_name, last_name, password=None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(
            username, first_name, last_name, password, **extra_fields
        )

    def _create_user(self, username, first_name, last_name, password, **extra_fields):
        if not username:
            raise ValueError("The given username must be set")
        if "email" in extra_fields:
            extra_fields["email"] = self.normalize_email(extra_fields["email"])
        username = User.normalize_username(username)
        user = self.model(
            username=username,
            first_name=first_name,
            last_name=last_name,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    username_validator = UnicodeUsernameValidator()

    id = models.AutoField(primary_key=True)
    username = models.CharField(
        _lazy("username"),
        max_length=150,
        unique=True,
        help_text=_lazy(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _lazy("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_lazy("first name"), max_length=255, blank=False)
    last_name = models.CharField(_lazy("last name"), max_length=255, blank=False)
    email = models.EmailField(
        _lazy("email address"),
        max_length=255,
        blank=True,
        null=True,
    )
    profile_image = models.ImageField(
        _lazy("profile image"),
        upload_to="public/profile_images",
        blank=True,
        null=True,
        help_text=_lazy("Resized to 256x256 px. If blank, default image will be used."),
    )
    is_staff = models.BooleanField(
        _lazy("staff status"),
        default=False,
        help_text=_lazy("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _lazy("active"),
        default=True,
        help_text=_lazy(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_lazy("date joined"), default=timezone.now)

    base_lecture_folder = models.OneToOneField(
        "lectures.LectureFolder",
        verbose_name=_lazy("base lecture folder"),
        on_delete=models.SET_NULL,
        related_name="user",
        blank=True,
        null=True,
        help_text=_lazy("Base lecture folder for the publisher."),
    )

    objects = UserManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ("first_name", "last_name")

    class Meta:
        verbose_name = _lazy("user")
        verbose_name_plural = _lazy("users")
        ordering = ["username"]

    def save(self, *args, **kwargs):
        handle_profile_image = False

        if self.pk:
            old = self.__class__.objects.get(pk=self.pk)

            # profile_image
            if old.profile_image != self.profile_image:
                handle_profile_image = self.profile_image is not None
                if old.profile_image:
                    old.profile_image.delete(False)
        else:
            handle_profile_image = self.profile_image is not None

        super().save(*args, **kwargs)

        # base lecture folder
        # this should be placed after save() because of `is_publisher()`
        if not self.base_lecture_folder and self.is_publisher():
            self.create_base_lecture_folder()
        elif (
            self.base_lecture_folder
            and self.base_lecture_folder.name != self.username.title()
        ):
            self.base_lecture_folder.name = self.username.title()
            self.base_lecture_folder.save(update_fields=["name"])

        if handle_profile_image:
            self.process_profile_image()

    def delete(self, *args, **kwargs):
        try:
            if self.base_lecture_folder:
                self.base_lecture_folder.delete()
        except Exception as e:
            logger.error(f"Failed to delete base lecture folder: {str(e)}")

        try:
            if self.profile_image:
                self.profile_image.delete(False)
        except Exception as e:
            logger.error(f"Failed to delete profile image: {str(e)}")

        super().delete(*args, **kwargs)

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        korean_pattern = re.compile("[가-힣]+")
        is_korean = korean_pattern.search(self.first_name) and korean_pattern.search(
            self.last_name
        )

        if is_korean:
            return f"{self.last_name}{self.first_name}"  # Korean format
        return f"{self.first_name} {self.last_name}"  # English format

    def is_admin(self):
        return self.is_staff

    def is_publisher(self):
        if self.is_admin():
            return False
        return self.groups.filter(profile__type=GroupProfile.Type.PUBLISHER).exists()

    def is_viewer(self):
        if self.is_admin() or self.is_publisher():
            return False
        return self.groups.filter(profile__type=GroupProfile.Type.VIEWER).exists()

    def create_base_lecture_folder(self):
        self.base_lecture_folder = LectureFolder.objects.create(
            name=self.username.title(),
            author=self.__class__.objects.filter(is_superuser=True).first(),
            manager=self,
        )
        self.__class__.objects.filter(pk=self.pk).update(
            base_lecture_folder=self.base_lecture_folder
        )

    def process_profile_image(self):
        try:
            image_path = self.profile_image.path
            with Image.open(image_path) as img:
                img = img.convert("RGB")

                # Crop to center square
                width, height = img.size
                min_dim = min(width, height)
                left = (width - min_dim) // 2
                top = (height - min_dim) // 2
                right = left + min_dim
                bottom = top + min_dim
                img = img.crop((left, top, right, bottom))

                # Resize to 256x256
                img = img.resize((256, 256), Image.Resampling.LANCZOS)

                img.save(image_path, format="JPEG")
        except Exception as e:
            logger.error(f"Failed to resize profile image: {str(e)}")
            self.profile_image.delete(False)


@receiver(m2m_changed, sender=User.groups.through)
def handle_user_group_change(sender, instance, action, **kwargs):
    if action in ["post_add"]:
        # base lecture folder
        if not instance.base_lecture_folder and instance.is_publisher():
            instance.create_base_lecture_folder()

    if action in ["post_add", "post_remove"]:
        # lecture content
        LectureContent.objects.handle_unavailable_by_user(instance)


@receiver(user_logged_out)
def clear_user_cache(sender, request, user, **kwargs):
    cache.delete_pattern(f"user_{user.id}_*")  # works with django_redis
