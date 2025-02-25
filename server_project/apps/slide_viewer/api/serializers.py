from rest_framework import serializers

from ..models import Annotation


class AnnotationSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", default=None)

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
        ]
        read_only_fields = ["author"]

    def validate(self, attrs):
        user = self.context["request"].user
        errors = {}

        slide = attrs.get("slide")
        if slide and not slide.user_can_view(user):
            errors["slide"] = "You don't have permission to view this slide."

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)
