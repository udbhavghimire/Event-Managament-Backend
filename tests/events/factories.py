import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from events.models import Event
from tests.accounts.factories import UserFactory


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    organizer = factory.SubFactory(UserFactory, role="organizer")
    title = factory.Sequence(lambda n: f"Test Event {n}")
    slug = factory.Sequence(lambda n: f"test-event-{n}")
    description = "A test event description."
    event_type = Event.EventType.IN_PERSON
    status = Event.Status.PUBLISHED
    starts_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=7))
    ends_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=7, hours=2))
    capacity = 100
    is_free = True
