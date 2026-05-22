"""
RegisterForEventService — orchestrates ticket purchase and confirmation.
Both free and paid flows share this service; only the entry point differs.
"""
import uuid

from django.conf import settings
from django.db import models, transaction
from django.db.models import F
from django.utils import timezone

from core.adapters.email_adapter import DjangoEmailSender, EmailSender, ResendEmailSender


def _default_email_sender() -> EmailSender:
    """Return the configured email sender based on EMAIL_PROVIDER setting."""
    if getattr(settings, "EMAIL_PROVIDER", "resend") == "resend":
        return ResendEmailSender()
    return DjangoEmailSender()


class SoldOutError(Exception):
    pass


class RegisterForEventService:
    def __init__(self, email_sender: EmailSender | None = None) -> None:
        self._email = email_sender or _default_email_sender()

    @transaction.atomic
    def execute(self, *, attendee, ticket_tier):
        """
        Free-event path: create a CONFIRMED registration immediately,
        increment quantity_sold, generate QR token, create a $0 payment
        record, and send ticket email.
        """
        from events.models import TicketTier
        from registrations.models import Payment, Registration

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

        Payment.objects.create(
            registration=registration,
            amount=tier.price,
            gateway_ref="FREE",
            status=Payment.Status.SUCCEEDED,
            paid_at=timezone.now(),
        )

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

    @transaction.atomic
    def request_refund(self, *, registration, reason: str):
        """Attendee requests a refund; awaits organizer approval."""
        from registrations.models import Payment, Refund, Registration

        if registration.status != Registration.Status.CONFIRMED:
            raise ValueError("Only confirmed registrations can request a refund.")

        try:
            payment = registration.payment
        except Payment.DoesNotExist:
            raise ValueError("No payment record found — cannot refund a free registration.")

        if payment.gateway_ref == "FREE" or payment.amount == 0:
            raise ValueError("Free registrations do not require a refund.")

        if payment.status == Payment.Status.REFUNDED:
            raise ValueError("This payment has already been refunded.")

        if Refund.objects.filter(
            registration=registration, status=Refund.Status.PENDING
        ).exists():
            raise ValueError("A refund request is already pending for this registration.")

        Refund.objects.create(
            registration=registration,
            amount=payment.amount,
            reason=reason,
            status=Refund.Status.PENDING,
        )
        registration.status = Registration.Status.REFUND_PENDING
        registration.save(update_fields=["status"])
        return registration

    @transaction.atomic
    def approve_refund(self, *, registration, gateway=None):
        """
        Organizer approves a pending refund: processes payment gateway refund,
        marks registration REFUNDED, and decrements quantity_sold.
        """
        from events.models import TicketTier
        from registrations.models import Payment, Refund, Registration

        if registration.status != Registration.Status.REFUND_PENDING:
            raise ValueError("This registration has no pending refund to approve.")

        refund = (
            Refund.objects.filter(
                registration=registration, status=Refund.Status.PENDING
            )
            .order_by("-requested_at")
            .first()
        )
        if refund is None:
            raise ValueError("No pending refund request found.")

        try:
            payment = registration.payment
        except Payment.DoesNotExist:
            raise ValueError("No payment record found.")

        if payment.status == Payment.Status.REFUNDED:
            raise ValueError("This payment has already been refunded.")

        if gateway is None:
            from core.adapters.payment_adapter import get_payment_gateway
            gateway = get_payment_gateway()

        result = gateway.refund(
            transaction_id=payment.gateway_ref,
            amount=payment.amount,
        )
        if not result.success:
            raise RuntimeError(f"Gateway refund failed: {result.error}")

        refund.status = Refund.Status.APPROVED
        refund.gateway_ref = result.transaction_id
        refund.refunded_at = timezone.now()
        refund.save(update_fields=["status", "gateway_ref", "refunded_at"])

        payment.status = Payment.Status.REFUNDED
        payment.save(update_fields=["status"])

        registration.status = Registration.Status.REFUNDED
        registration.save(update_fields=["status"])

        TicketTier.objects.filter(pk=registration.ticket_tier_id).update(
            quantity_sold=models.F("quantity_sold") - 1
        )

        return registration

    @transaction.atomic
    def reject_refund(self, *, registration):
        """Organizer rejects a pending refund request."""
        from registrations.models import Refund, Registration

        if registration.status != Registration.Status.REFUND_PENDING:
            raise ValueError("This registration has no pending refund to reject.")

        refund = (
            Refund.objects.filter(
                registration=registration, status=Refund.Status.PENDING
            )
            .order_by("-requested_at")
            .first()
        )
        if refund is None:
            raise ValueError("No pending refund request found.")

        refund.status = Refund.Status.REJECTED
        refund.save(update_fields=["status"])

        registration.status = Registration.Status.CONFIRMED
        registration.save(update_fields=["status"])
        return registration

    def _send_ticket_safe(self, registration) -> None:
        """Send ticket email, silently swallowing errors so the DB transaction isn't rolled back."""
        try:
            self._email.send_ticket(registration=registration)
        except Exception:
            pass
