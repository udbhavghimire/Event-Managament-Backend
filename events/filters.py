import django_filters
from .models import Event


class EventFilter(django_filters.FilterSet):
    """
    Supports ?status=PUBLISHED and ?from=YYYY-MM-DD.
    The 'from' date param is handled manually in the view because
    'from' is a Python reserved word.
    Full-text ?search= is handled by DRF's SearchFilter backend.
    """
    status = django_filters.ChoiceFilter(choices=Event.Status.choices)

    class Meta:
        model = Event
        fields = ["status"]
