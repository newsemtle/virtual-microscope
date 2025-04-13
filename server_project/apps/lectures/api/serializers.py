from rest_framework import serializers
from rest_framework.reverse import reverse

from ..models import Lecture, LectureContent, LectureFolder


class LectureFolderSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", default=None)

    class Meta:
        model = LectureFolder
        fields = [
            "id",
            "name",
            "author",
            "parent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author"]

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        parent = attrs.get("parent")
        if parent and not parent.is_owner(user):
            errors["parent"] = "You don't have permission to edit this folder."

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
    author = serializers.CharField(source="author.username", default=None)
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
            "folder",
            "contents",
            "groups",
            "is_active",
            "created_at",
            "updated_at",
            "edit_url",
            "folder_url",
        ]
        read_only_fields = ["author"]

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        folder = attrs.get("folder")
        if folder and not folder.is_owner(user):
            errors["folder"] = "You don't have permission to edit this folder."

        contents = attrs.get("contents", [])
        for index, content in enumerate(contents):
            slide = content.get("slide")
            annotation = content.get("annotation")
            if slide and not slide.user_can_view(user):
                errors[f"contents[{index}].slide"] = (
                    "You don't have permission to view this slide."
                )
            if annotation and not annotation.user_can_view(user):
                errors[f"contents[{index}].annotation"] = (
                    "You don't have permission to view this annotation."
                )

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        contents_data = validated_data.pop("contents", [])

        lecture = super().create(validated_data)

        for content in contents_data:
            LectureContent.objects.create(lecture=lecture, **content)

        return lecture

    def update(self, instance, validated_data):
        contents_data = validated_data.pop("contents", [])
        lecture = super().update(instance, validated_data)

        lecture.contents.all().delete()
        for content in contents_data:
            LectureContent.objects.create(lecture=lecture, **content)

        lecture.save()
        return lecture

    def get_edit_url(self, obj):
        return reverse("lectures:lecture-edit", kwargs={"lecture_id": obj.pk})

    def get_folder_url(self, obj):
        return reverse("lectures:lecture-database") + f"?folder={obj.folder.id}"
