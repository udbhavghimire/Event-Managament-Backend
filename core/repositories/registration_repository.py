from django.db.models import QuerySet

from registrations.models import Registration
from .base import BaseRepository


class RegistrationRepository(BaseRepository[Registration]):
    model = Registration

    def get_for_event(self, event_id: int) -> QuerySet[Registration]:
        return self.filter(event_id=event_id).select_related("attendee")

    def get_for_attendee(self, attendee_id: int) -> QuerySet[Registration]:
        return self.filter(attendee_id=attendee_id).select_related("event")

    def get_confirmed_count(self, event_id: int) -> int:
        return self.filter(event_id=event_id, status=Registration.Status.CONFIRMED).count()

    def get_by_reference(self, reference) -> Registration | None:
        try:
            return self.model.objects.select_related("event", "attendee").get(reference=reference)
        except self.model.DoesNotExist:
            return None
