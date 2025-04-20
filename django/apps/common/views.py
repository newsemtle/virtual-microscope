from django.views.generic import TemplateView

from config import __version__


class HomeView(TemplateView):
    template_name = "common/home.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)

        context["show_database"] = False
        context["show_lecture_database"] = False
        if user.is_authenticated:
            if user.is_admin() or user.is_publisher():
                context["show_database"] = True
                context["show_lecture_database"] = True

        context["VERSION"] = __version__
        return context
