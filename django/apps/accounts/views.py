from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView

from apps.accounts.forms import UserChangeForm


class LoginView(TemplateView):
    template_name = "accounts/login.html"


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"


class ProfileEditView(LoginRequiredMixin, FormView):
    template_name = "accounts/profile_edit.html"
    form_class = UserChangeForm
    success_url = reverse_lazy("accounts:profile")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.profile_image:
            context["profile_image_url"] = self.request.user.profile_image.url
        context["email_value"] = self.request.user.email
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            user = request.user
            user.email = form.cleaned_data["email"]
            if form.cleaned_data["profile_image"]:
                user.profile_image = form.cleaned_data["profile_image"]
            if form.cleaned_data["delete_image"]:
                user.profile_image.delete(False)
                user.profile_image = None
            user.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
