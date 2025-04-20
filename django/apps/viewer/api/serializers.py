from django.urls import reverse
from rest_framework import serializers

from apps.viewer.models import Annotation


class AnnotationSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", default=None)
    url = serializers.SerializerMethodField()
    viewer_url = serializers.SerializerMethodField()
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
            "url",
            "viewer_url",
            "editable",
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

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)

    def get_url(self, obj):
        return reverse("api:annotation-detail", kwargs={"pk": obj.pk})

    def get_viewer_url(self, obj):
        return reverse("viewer:image-viewer", kwargs={"slide_id": obj.slide.pk}) + f"?annotation={obj.pk}"

    def get_editable(self, obj):
        return obj.user_can_edit(self.context["request"].user)
