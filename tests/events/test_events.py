import pytest
from django.urls import reverse
from rest_framework import status

from tests.events.factories import EventFactory
from tests.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestEventList:
    def test_list_published_events_unauthenticated(self, api_client):
        EventFactory.create_batch(3, status="published")
        url = reverse("events:event_list_create")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3

    def test_create_event_requires_auth(self, api_client):
        url = reverse("events:event_list_create")
        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestEventDetail:
    def test_retrieve_by_slug(self, api_client):
        event = EventFactory(status="published")
        url = reverse("events:event_detail", kwargs={"slug": event.slug})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["slug"] == event.slug

    def test_non_organizer_cannot_update(self, api_client):
        event = EventFactory(status="published")
        other_user = UserFactory()
        api_client.force_authenticate(user=other_user)
        url = reverse("events:event_detail", kwargs={"slug": event.slug})
        response = api_client.patch(url, {"title": "Hacked"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
