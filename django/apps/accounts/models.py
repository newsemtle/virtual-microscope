import logging

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
from django.db import models
from django.db.models import Q
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.images.models import ImageFolder
from apps.lectures.models import LectureFolder

logger = logging.getLogger("django")


class GroupProfile(models.Model):
    class Type(models.TextChoices):
        PUBLISHER = ("1", "Publisher")
        VIEWER = ("2", "Viewer")

    id = models.AutoField(primary_key=True)
    group = models.OneToOneField(
        "auth.Group", on_delete=models.CASCADE, related_name="profile"
    )
    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        blank=False,
        help_text="Type of the group.",
    )
    base_folder = models.OneToOneField(
        "images.ImageFolder",
        on_delete=models.CASCADE,
        related_name="groupprofile",
        blank=True,
        null=True,
        help_text="Base folder for the publisher group.",
    )

    def __str__(self):
        return f"Profile for '{self.group.name}' group"

    def save(self, *args, **kwargs):
        created = False if self.pk else True

        super().save(*args, **kwargs)

        if created:
            self.set_default_permission()

    def delete(self, *args, **kwargs):
        try:
            if self.group:
                self.group.delete()
        except Exception as e:
            logger.error(f"Failed to delete group: {str(e)}")

        try:
            if self.base_folder:
                self.base_folder.delete()
        except Exception as e:
            logger.error(f"Failed to delete base folder: {str(e)}")

        super().delete(*args, **kwargs)

    def set_default_permission(self):
        if self.is_publisher_group():
            q = Q(content_type__app_label="images")
            q |= Q(content_type__app_label="lectures")
            q |= Q(content_type__model="annotation")
            self.group.permissions.set(Permission.objects.filter(q))
        elif self.is_viewer_group():
            q = Q(content_type__model="slide", codename__contains="view")
            q |= Q(content_type__model="lecture", codename__contains="view")
            q |= Q(content_type__model="lecturecontent", codename__contains="view")
            q |= Q(content_type__model="annotation", codename__contains="view")
            self.group.permissions.set(Permission.objects.filter(q))

    def is_publisher_group(self):
        return self.type == self.Type.PUBLISHER

    def is_viewer_group(self):
        return self.type == self.Type.VIEWER


@receiver(post_save, sender=Group)
def update_group_profile(sender, instance, created, **kwargs):
    profile = instance.profile
    if profile and profile.is_publisher_group():
        if profile.base_folder:
            base_folder = profile.base_folder
            if base_folder.name != instance.name.title():
                base_folder.name = instance.name.title()
                base_folder.save(update_fields=["name"])
        else:
            profile.base_folder = ImageFolder.objects.create(
                name=instance.name.title(),
                author=User.objects.filter(is_superuser=True).first(),
                manager_group=instance,
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
    id = models.AutoField(primary_key=True)
    username = models.CharField(
        "username",
        max_length=150,
        unique=True,
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
        validators=[UnicodeUsernameValidator()],
        error_messages={
            "unique": "A user with that username already exists.",
        },
    )
    email = models.EmailField("email address", max_length=255, blank=True, null=True)
    first_name = models.CharField("first name", max_length=255, blank=False)
    last_name = models.CharField("last name", max_length=255, blank=False)
    profile_image = models.ImageField(
        "profile image",
        upload_to="public/profile_images",
        blank=True,
        null=True,
    )
    base_lecture_folder = models.OneToOneField(
        "lectures.LectureFolder",
        on_delete=models.SET_NULL,
        related_name="user",
        blank=True,
        null=True,
        help_text="Base lecture folder for the publisher.",
    )

    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text="Designates whether this user should be treated as active.\nUnselect this instead of deleting accounts.",
    )
    date_joined = models.DateTimeField("date joined", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ("first_name", "last_name")

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = self.__class__.objects.get(pk=self.pk)
            if old_instance.username != self.username and self.base_lecture_folder:
                self.base_lecture_folder.name = self.username.title()
                self.base_lecture_folder.save(update_fields=["name"])
            if old_instance.profile_image != self.profile_image:
                if old_instance.profile_image:
                    old_instance.profile_image.delete(False)

        super().save(*args, **kwargs)

        if self.is_publisher() and not self.base_lecture_folder:
            self.base_lecture_folder = LectureFolder.objects.create(
                name=self.username.title(),
                author=self.__class__.objects.filter(is_superuser=True).first(),
                manager=self,
            )
            self.__class__.objects.filter(pk=self.pk).update(
                base_lecture_folder=self.base_lecture_folder
            )

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
        return f"{self.first_name} {self.last_name}".strip()

    def get_korean_name(self):
        return f"{self.last_name}{self.first_name}".strip()

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


@receiver(m2m_changed, sender=User.groups.through)
def create_lecture_folder_on_publisher_add(sender, instance, action, **kwargs):
    if action in ["post_add"]:
        if instance.is_publisher() and not instance.base_lecture_folder:
            instance.base_lecture_folder = LectureFolder.objects.create(
                name=instance.username.title(),
                author=User.objects.filter(is_superuser=True).first(),
                manager=instance,
            )
            instance.save(update_fields=["base_lecture_folder"])


@receiver(user_logged_out)
def clear_user_cache(sender, request, user, **kwargs):
    cache.delete_pattern(f"user_{user.id}_*")  # works with django_redis
