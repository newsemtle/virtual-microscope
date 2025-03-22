from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from . import forms


class RegistrationView(CreateView):
    form_class = forms.UserCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("home")


class LoginView(auth_views.LoginView):
    form_class = forms.LoginForm
    template_name = "accounts/login.html"

    def form_valid(self, form):
        expire_time = None
        if form.cleaned_data["remember_me"]:
            expire_time = 60 * 60 * 24 * 1  # 1 day
        self.request.session.set_expiry(expire_time)
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
