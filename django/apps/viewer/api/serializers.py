from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.viewer.models import Annotation


class AnnotationSerializer(serializers.ModelSerializer):
    author = serializers.CharField(
        source="author.username", default=None, read_only=True
    )
    editable = serializers.SerializerMethodField()

    class Meta:
        model = Annotation
        fields = [
            "id",
            "name",
            "description",
            "data",
            "slide",
            "author",
            "created_at",
            "updated_at",
            "editable",
        ]
        read_only_fields = []

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        slide = attrs.get("slide")
        if slide and not slide.is_viewable_by(user):
            errors["slide"] = _("You don't have permission to view this slide.")

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user

        author = validated_data["author"]
        slide = validated_data["slide"]
        name = validated_data["name"]
        if Annotation.objects.filter(author=author, slide=slide, name=name).exists():
            raise serializers.ValidationError(
                {"detail": _("Annotation with this name already exists.")}
            )

        return super().create(validated_data)

    def get_editable(self, obj):
        return obj.is_editable_by(self.context["request"].user)
