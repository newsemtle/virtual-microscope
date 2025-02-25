from django import forms
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import get_user_model

User = get_user_model()


class UserCreationForm(auth_forms.UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")


class UserChangeForm(auth_forms.UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class LoginForm(auth_forms.AuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=False)


class PasswordChangeForm(auth_forms.PasswordChangeForm):
    model = User
