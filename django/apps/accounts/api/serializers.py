from django.contrib.auth import authenticate
from django.utils.translation import gettext as _
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(username=data["username"], password=data["password"])
        if user is None:
            raise serializers.ValidationError(_("Invalid username or password."))
        data["user"] = user
        return data
