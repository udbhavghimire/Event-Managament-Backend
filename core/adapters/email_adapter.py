"""
Email adapter — abstract interface + Django-backed implementation.
Swap EmailSender for a SendGrid or Mailgun concrete class in production.
"""
import abc

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


class EmailSender(abc.ABC):
    """Abstract contract every email provider must satisfy."""

    @abc.abstractmethod
    def send(self, *, subject: str, recipient: str, template: str, context: dict) -> int:
        """Send a templated email. Returns number of messages sent."""
        ...

    @abc.abstractmethod
    def send_ticket(self, *, registration) -> int:
        """Send a booking confirmation with QR token to the attendee."""
        ...


class DjangoEmailSender(EmailSender):
    """Concrete implementation backed by Django's email backend."""

    def send(self, *, subject: str, recipient: str, template: str, context: dict) -> int:
        html_body = render_to_string(template, context)
        return send_mail(
            subject=subject,
            message="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_body,
            fail_silently=False,
        )

    def send_ticket(self, *, registration) -> int:
        return self.send(
            subject=f"Your ticket — {registration.ticket_tier.event.title}",
            recipient=registration.attendee.user.email,
            template="emails/ticket.html",
            context={"registration": registration},
        )
