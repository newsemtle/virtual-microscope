from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
    Permission,
)
from django.contrib.auth.models import Group
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from apps.database.models import Folder
from apps.lectures.models import LectureFolder


class GroupProfile(models.Model):
    class TypeChoices(models.TextChoices):
        PUBLISHER = ("1", "Publisher")
        VIEWER = ("2", "Viewer")

    id = models.AutoField(primary_key=True)
    group = models.OneToOneField(
        "auth.Group", on_delete=models.CASCADE, related_name="profile"
    )
    type = models.CharField(
        max_length=10,
        choices=TypeChoices,
        blank=False,
        help_text="Type of the group.",
    )
    base_folder = models.OneToOneField(
        "database.Folder",
        on_delete=models.CASCADE,
        related_name="groupprofile",
        blank=True,
        null=True,
        help_text="Base folder for the publisher group.",
    )

    def __str__(self):
        return f"Profile for {self.group.name} group"

    def save(self, *args, **kwargs):
        created = False if self.pk else True

        if created and self.type == self.TypeChoices.PUBLISHER:
            self.base_folder = Folder.objects.create(name=self.group.name.title())

        super().save(*args, **kwargs)

        if created:
            self.set_default_permission()

    def set_default_permission(self):
        if self.type == self.TypeChoices.PUBLISHER:
            permissions = Permission.objects.filter(content_type__app_label="database")
            permissions |= Permission.objects.filter(content_type__app_label="lectures")
            permissions |= Permission.objects.filter(
                content_type__app_label="slide_viewer"
            )
            self.group.permissions.set(permissions)
        elif self.type == self.TypeChoices.VIEWER:
            permissions = Permission.objects.filter(
                content_type__model="slide", codename__contains="view"
            )
            permissions |= Permission.objects.filter(
                content_type__model="lecture", codename__contains="view"
            )
            permissions |= Permission.objects.filter(
                content_type__model="lecturecontent", codename__contains="view"
            )
            permissions |= Permission.objects.filter(
                content_type__app_label="slide_viewer", codename__contains="view"
            )
            self.group.permissions.set(permissions)


@receiver(post_delete, sender=GroupProfile)
def delete_base_folder(sender, instance, **kwargs):
    if instance.group:
        instance.group.delete()
    if instance.base_folder:
        instance.base_folder.delete()


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
    first_name = models.CharField("first name", max_length=255, blank=True)
    last_name = models.CharField("last name", max_length=255, blank=True)
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
        super().save(*args, **kwargs)

        if (
            not self.base_lecture_folder
            and self.groups.filter(
                profile__type=GroupProfile.TypeChoices.PUBLISHER
            ).exists()
        ):
            self.base_lecture_folder = LectureFolder.objects.create(
                name=self.username.title()
            )
            self.save(update_fields=["base_lecture_folder"])

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def is_admin(self):
        return self.is_staff
