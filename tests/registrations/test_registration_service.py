import pytest

from core.services.registration_service import (
    CapacityExceededError,
    DuplicateRegistrationError,
    RegistrationService,
)
from tests.accounts.factories import UserFactory
from tests.events.factories import EventFactory

pytestmark = pytest.mark.django_db


class TestRegistrationService:
    def setup_method(self):
        self.service = RegistrationService()

    def test_register_free_event(self):
        user = UserFactory()
        event = EventFactory(is_free=True, capacity=10)
        reg = self.service.register(attendee_id=user.pk, event_id=event.pk)
        assert reg.pk is not None
        assert reg.status == "confirmed"

    def test_duplicate_registration_raises(self):
        user = UserFactory()
        event = EventFactory(capacity=10)
        self.service.register(attendee_id=user.pk, event_id=event.pk)
        with pytest.raises(DuplicateRegistrationError):
            self.service.register(attendee_id=user.pk, event_id=event.pk)

    def test_capacity_exceeded_raises(self):
        event = EventFactory(capacity=1)
        user1 = UserFactory()
        user2 = UserFactory()
        self.service.register(attendee_id=user1.pk, event_id=event.pk)
        with pytest.raises(CapacityExceededError):
            self.service.register(attendee_id=user2.pk, event_id=event.pk)

    def test_cancel_registration(self):
        user = UserFactory()
        event = EventFactory(capacity=10)
        reg = self.service.register(attendee_id=user.pk, event_id=event.pk)
        cancelled = self.service.cancel(registration_id=reg.pk, requester_id=user.pk)
        assert cancelled.status == "cancelled"
