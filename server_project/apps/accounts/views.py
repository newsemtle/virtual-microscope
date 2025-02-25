from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from . import forms


class HomeView(TemplateView):
    template_name = "accounts/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["show_database"] = self.request.user.has_perm(
                "database.view_folder"
            )
            context["show_lecture_database"] = self.request.user.has_perm(
                "lectures.view_lecture"
            )
        else:
            context["show_database"] = False
            context["show_lecture_database"] = False
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
