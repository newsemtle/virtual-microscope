from django.utils.translation import gettext as _, gettext_lazy as _lazy
from rest_framework import serializers
from rest_framework.reverse import reverse

from apps.lectures.models import Lecture, LectureContent, LectureFolder


class LectureFolderSerializer(serializers.ModelSerializer):
    author = serializers.CharField(
        source="author.username", default=None, read_only=True
    )
    manager = serializers.CharField(
        source="manager.username", default=None, read_only=True
    )

    class Meta:
        model = LectureFolder
        fields = [
            "id",
            "name",
            "author",
            "manager",
            "parent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = []
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=LectureFolder.objects.all(),
                fields=("name", "parent"),
                message=_lazy(
                    "The folder with the name already exists in this location."
                ),
            )
        ]

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        parent_is_sent = "parent" in self.initial_data
        parent = attrs.get("parent")

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


class LectureContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LectureContent
        fields = ["id", "slide", "annotation", "order"]


class LectureSerializer(serializers.ModelSerializer):
    author = serializers.CharField(
        source="author.username", default=None, read_only=True
    )
    manager = serializers.CharField(
        source="manager.username", default=None, read_only=True
    )
    contents = LectureContentSerializer(many=True, required=False)
    edit_url = serializers.SerializerMethodField()
    folder_url = serializers.SerializerMethodField()

    class Meta:
        model = Lecture
        fields = [
            "id",
            "name",
            "description",
            "author",
            "manager",
            "folder",
            "contents",
            "viewer_groups",
            "is_open",
            "created_at",
            "updated_at",
            "edit_url",
            "folder_url",
        ]
        read_only_fields = []

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        folder_is_sent = "folder" in self.initial_data
        folder = attrs.get("folder")

        if folder_is_sent:
            if not folder:
                errors["detail"] = _("You can't place lecture at the root location.")
            elif folder and not folder.is_managed_by(user):
                errors["detail"] = _("You don't have permission to edit this lecture.")

        contents = attrs.get("contents", [])
        for index, content in enumerate(contents):
            slide = content.get("slide")
            annotation = content.get("annotation")
            if slide and not slide.is_viewable_by(user):
                errors[f"detail"] = _(
                    "You don't have permission to view slide '{name}'."
                ).format(name=slide.name)
            if annotation and not annotation.is_viewable_by(user):
                errors[f"detail"] = _(
                    "You don't have permission to view annotation '{name}'."
                ).format(name=annotation.name)

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        contents_data = validated_data.pop("contents", [])

        lecture = super().create(validated_data)

        for content in contents_data:
            lecture.contents.create(**content)

        return lecture

    def update(self, instance, validated_data):
        contents_data = validated_data.pop("contents", [])
        lecture = super().update(instance, validated_data)

        lecture.contents.all().delete()
        for content in contents_data:
            lecture.contents.create(**content)

        lecture.save()
        return lecture

    def get_edit_url(self, obj):
        return reverse("lectures:lecture-edit", kwargs={"lecture_id": obj.pk})

    def get_folder_url(self, obj):
        return reverse("lectures:lecture-database") + f"?folder={obj.folder.id}"
