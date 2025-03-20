import django_filters
from django.contrib.auth import get_user_model

from .models import Tag, Slide

User = get_user_model()


class SlideFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    author = django_filters.ModelChoiceFilter(
        field_name="author__username",
        to_field_name="username",
        queryset=User.objects.all(),
    )
    tags = django_filters.ModelMultipleChoiceFilter(queryset=Tag.objects.all())

    class Meta:
        model = Slide
        fields = ["name", "author", "tags"]
