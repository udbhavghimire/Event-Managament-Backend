"""
High-level email helpers used by the rest of the application.
Uses EmailSender (adapter) so the underlying provider can be swapped freely.
"""
from core.adapters.email_adapter import DjangoEmailSender, EmailSender


class EmailService:
    def __init__(self, sender: EmailSender | None = None) -> None:
        self._sender = sender or DjangoEmailSender()

    def send_registration_confirmation(self, *, registration) -> int:
        return self._sender.send(
            subject=f"Registration confirmed — {registration.event.title}",
            recipient=registration.attendee.email,
            template="emails/registration_confirmation.html",
            context={"registration": registration},
        )

    def send_cancellation_notice(self, *, registration) -> int:
        return self._sender.send(
            subject=f"Registration cancelled — {registration.event.title}",
            recipient=registration.attendee.email,
            template="emails/registration_cancellation.html",
            context={"registration": registration},
        )
