import os

from django.urls import reverse
from rest_framework import serializers

from apps.images.models import Slide, ImageFolder, Tag


class ImageFolderSerializer(serializers.ModelSerializer):
    author = serializers.CharField(
        source="author.username", default=None, read_only=True
    )
    manager_group = serializers.CharField(
        source="manager_group.name", default=None, read_only=True
    )
    url = serializers.SerializerMethodField()

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
            "url",
        ]
        read_only_fields = []
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=ImageFolder.objects.all(),
                fields=("name", "parent"),
                message="The folder name already exists in this folder",
            )
        ]

    def validate(self, attrs):
        user = self.context["request"].user
        parent_is_sent = "parent" in self.initial_data
        parent = attrs.get("parent")

        errors = {}

        if parent_is_sent:
            if not parent and not user.is_admin():
                errors["detail"] = "You can't place folder at the root location."
            elif parent and not parent.is_managed_by(user):
                errors["detail"] = "You don't have permission to edit this folder."
        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)

    def get_url(self, obj):
        return reverse("api:image-folder-items", kwargs={"pk": obj.pk})


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
    thumbnail = serializers.SerializerMethodField()
    associated_image = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    url = serializers.SerializerMethodField()
    view_url = serializers.SerializerMethodField()
    annotations_url = serializers.SerializerMethodField()

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
            "thumbnail",
            "associated_image",
            "metadata",
            "is_public",
            "tags",
            "build_status",
            "created_at",
            "updated_at",
            "url",
            "view_url",
            "annotations_url",
        ]
        read_only_fields = ["image_root", "metadata"]

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        folder = attrs.get("folder")
        if folder and not folder.is_managed_by(user):
            errors["detail"] = "You don't have permission to edit this folder."

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

    def get_thumbnail(self, obj):
        return reverse("api:slide-thumbnail", kwargs={"pk": obj.pk})

    def get_associated_image(self, obj):
        return reverse("api:slide-associated-image", kwargs={"pk": obj.pk})

    def get_url(self, obj):
        return reverse("api:slide-detail", kwargs={"pk": obj.pk})

    def get_view_url(self, obj):
        return reverse("viewer:image-viewer", kwargs={"slide_id": obj.pk})

    def get_annotations_url(self, obj):
        return reverse("api:slide-annotations", kwargs={"pk": obj.pk})
