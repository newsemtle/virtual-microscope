from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class LoginView(TemplateView):
    template_name = "accounts/login.html"


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
