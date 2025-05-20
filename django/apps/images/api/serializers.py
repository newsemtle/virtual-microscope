import os

from django.utils.translation import gettext as _, gettext_lazy as _lazy
from rest_framework import serializers

from apps.images.models import Slide, ImageFolder, Tag


class ImageFolderSerializer(serializers.ModelSerializer):
    author = serializers.CharField(
        source="author.username", default=None, read_only=True
    )
    manager_group = serializers.CharField(
        source="manager_group.name", default=None, read_only=True
    )

    class Meta:
        model = ImageFolder
        fields = [
            "id",
            "name",
            "author",
            "manager_group",
            "parent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = []
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=ImageFolder.objects.all(),
                fields=("name", "parent"),
                message=_lazy(
                    "The folder with the name already exists in this location."
                ),
            )
        ]

    def validate(self, attrs):
        user = self.context["request"].user
        parent_is_sent = "parent" in self.initial_data
        parent = attrs.get("parent")

        errors = {}

        if parent_is_sent:
            if not parent:
                errors["detail"] = _("You can't place folder at the root location.")
            elif parent and not parent.is_managed_by(user):
                errors["detail"] = _("You don't have permission to edit this folder.")
        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            "id",
            "name",
            "author",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        return instance.tag.name


class SlideSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_blank=True)
    author = serializers.CharField(
        source="author.username", default=None, read_only=True
    )
    manager_group = serializers.CharField(
        source="manager_group.name", default=None, read_only=True
    )
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Slide
        fields = [
            "id",
            "name",
            "information",
            "author",
            "manager_group",
            "folder",
            "file",
            "image_root",
            "metadata",
            "is_public",
            "tags",
            "build_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["image_root", "metadata"]

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        folder = attrs.get("folder")
        if folder and not folder.is_managed_by(user):
            errors["detail"] = _("You don't have permission to edit this slide.")

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)

    def create(self, validated_data):
        if not validated_data.get("name"):
            validated_data["name"] = os.path.splitext(
                os.path.basename(validated_data.get("file").name)
            )[0]

        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)
