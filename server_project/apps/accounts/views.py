from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from . import forms


class HomeView(TemplateView):
    template_name = "accounts/home.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)

        context["show_database"] = False
        context["show_lecture_database"] = False
        if user.is_authenticated:
            if user.is_admin() or user.is_publisher():
                context["show_database"] = True
                context["show_lecture_database"] = True

        context["VERSION"] = settings.VERSION
        return context


class RegistrationView(CreateView):
    form_class = forms.UserCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("home")


class LoginView(auth_views.LoginView):
    form_class = forms.LoginForm
    template_name = "accounts/login.html"

    def form_valid(self, form):
        if not form.cleaned_data["remember_me"]:
            self.request.session.set_expiry(0)
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
