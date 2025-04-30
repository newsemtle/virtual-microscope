import django_filters
from django.contrib.auth.models import Group

from apps.images.models import Slide


# 현재 쓰이는 곳 없음
class SlideFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    manager_group = django_filters.ModelChoiceFilter(
        field_name="manager_group__name",
        to_field_name="name",
        queryset=Group.objects.all(),
    )

    class Meta:
        model = Slide
        fields = ["name", "manager_group"]
