import pytest
from django.urls import reverse
from rest_framework import status

from tests.accounts.factories import UserFactory
from tests.events.factories import EventFactory

pytestmark = pytest.mark.django_db


class TestEventStats:
    def test_stats_requires_organizer_role(self, api_client):
        attendee = UserFactory(role="attendee")
        event = EventFactory()
        api_client.force_authenticate(user=attendee)
        url = reverse("analytics:event_stats", kwargs={"event_id": event.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_organizer_can_view_own_event_stats(self, api_client):
        organizer = UserFactory(role="organizer")
        event = EventFactory(organizer=organizer)
        api_client.force_authenticate(user=organizer)
        url = reverse("analytics:event_stats", kwargs={"event_id": event.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["event_id"] == event.pk
        assert "total_registrations" in response.data
        assert "fill_rate" in response.data

    def test_organizer_cannot_view_other_event_stats(self, api_client):
        organizer = UserFactory(role="organizer")
        other_event = EventFactory()  # owned by a different organizer
        api_client.force_authenticate(user=organizer)
        url = reverse("analytics:event_stats", kwargs={"event_id": other_event.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
