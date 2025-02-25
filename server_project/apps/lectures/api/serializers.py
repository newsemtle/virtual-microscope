from rest_framework import serializers

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
        if parent and not parent.user_can_edit(user):
            errors["parent"] = "You don't have permission to edit this folder."

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)


class LectureContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LectureContent
        fields = ["id", "slide", "annotation", "order"]


class LectureSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", default=None)
    contents = LectureContentSerializer(many=True, required=False)

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
        ]
        read_only_fields = ["author"]

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        folder = attrs.get("folder")
        if folder and not folder.user_can_edit(user):
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
