from django import forms
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _, gettext_lazy as _lazy

User = get_user_model()


class AdminUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label=_lazy("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(
        label=_lazy("Password confirmation"), widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Passwords don't match"))
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AdminUserChangeForm(auth_forms.UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class AdminPasswordChangeForm(forms.Form):
    password1 = forms.CharField(label=_lazy("New Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(
        label=_lazy("New Password Confirmation"), widget=forms.PasswordInput
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs["autofocus"] = True

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["set_usable_password"] = True
        return cleaned_data

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Passwords don't match"))
        return password2

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data["password1"])
        if commit:
            self.user.save()
        return self.user


class UserChangeForm(forms.ModelForm):
    delete_image = forms.BooleanField(required=False, label=_lazy("Delete Image"))

    class Meta:
        model = User
        fields = ["email", "profile_image"]
