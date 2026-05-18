"""
RegisterForEventService — orchestrates ticket purchase and confirmation.
Both free and paid flows share this service; only the entry point differs.
"""
import uuid

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.adapters.email_adapter import DjangoEmailSender, EmailSender


class SoldOutError(Exception):
    pass


class RegisterForEventService:
    def __init__(self, email_sender: EmailSender | None = None) -> None:
        self._email = email_sender or DjangoEmailSender()

    @transaction.atomic
    def execute(self, *, attendee, ticket_tier):
        """
        Free-event path: create a CONFIRMED registration immediately,
        increment quantity_sold, generate QR token, send ticket email.
        """
        from events.models import TicketTier
        from registrations.models import Registration

        # Re-select with a row lock to prevent over-selling
        tier = TicketTier.objects.select_for_update().get(pk=ticket_tier.pk)
        if tier.quantity_sold >= tier.quantity_total:
            raise SoldOutError("No tickets available for this tier.")

        qr_code = uuid.uuid4().hex
        registration = Registration.objects.create(
            attendee=attendee,
            ticket_tier=tier,
            status=Registration.Status.CONFIRMED,
            qr_code=qr_code,
        )

        TicketTier.objects.filter(pk=tier.pk).update(quantity_sold=F("quantity_sold") + 1)

        self._send_ticket_safe(registration)
        return registration

    @transaction.atomic
    def confirm(self, *, registration, gateway_ref: str):
        """
        Paid-event confirmation path: called after server-side payment verification.
        Sets CONFIRMED, increments quantity_sold, creates Payment row,
        generates QR token, sends ticket email.
        """
        from django.utils import timezone
        from events.models import TicketTier
        from registrations.models import Payment, Registration

        # Row-lock the tier to prevent over-selling
        tier = TicketTier.objects.select_for_update().get(pk=registration.ticket_tier_id)
        if tier.quantity_sold >= tier.quantity_total:
            raise SoldOutError("No tickets available for this tier.")

        qr_code = uuid.uuid4().hex
        registration.status = Registration.Status.CONFIRMED
        registration.qr_code = qr_code
        registration.save(update_fields=["status", "qr_code"])

        TicketTier.objects.filter(pk=tier.pk).update(quantity_sold=F("quantity_sold") + 1)

        Payment.objects.create(
            registration=registration,
            amount=tier.price,
            gateway_ref=gateway_ref,
            status=Payment.Status.SUCCEEDED,
            paid_at=timezone.now(),
        )

        self._send_ticket_safe(registration)
        return registration

    def _send_ticket_safe(self, registration) -> None:
        """Send ticket email, silently swallowing errors so the DB transaction isn't rolled back."""
        try:
            self._email.send_ticket(registration=registration)
        except Exception:
            pass
