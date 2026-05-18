from django.db.models import QuerySet

from events.models import Event
from .base import BaseRepository


class EventRepository(BaseRepository[Event]):
    model = Event

    def get_published(self) -> QuerySet[Event]:
        return self.filter(status=Event.Status.PUBLISHED).select_related("organizer", "category")

    def get_by_organizer(self, organizer_id: int) -> QuerySet[Event]:
        return self.filter(organizer_id=organizer_id)

    def get_by_slug(self, slug: str) -> Event | None:
        try:
            return self.model.objects.select_related("organizer", "category").get(slug=slug)
        except self.model.DoesNotExist:
            return None
