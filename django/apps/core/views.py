from django.views.generic import TemplateView

from config import __version__


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)
        context["VERSION"] = __version__
        return context
