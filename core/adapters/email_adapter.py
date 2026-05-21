"""
Email adapter — abstract interface + concrete implementations.
  - DjangoEmailSender  : Django SMTP backend (dev / fallback)
  - ResendEmailSender  : Resend API (production)

Switch by setting EMAIL_PROVIDER=resend in .env (default: resend).
"""
import abc
import base64
import io

from django.conf import settings
from django.template.loader import render_to_string


class EmailSender(abc.ABC):
    """Abstract contract every email provider must satisfy."""

    @abc.abstractmethod
    def send(self, *, subject: str, recipient: str, template: str, context: dict) -> int:
        """Send a templated email. Returns number of messages sent."""
        ...

    @abc.abstractmethod
    def send_ticket(self, *, registration) -> int:
        """Send a booking confirmation with QR code image to the attendee."""
        ...


def _generate_qr_base64(data: str) -> str:
    """
    Render *data* as a QR code PNG and return a base64-encoded data URI
    suitable for embedding directly in HTML: data:image/png;base64,...
    Uses Pillow (PIL) as the image backend (installed via qrcode[pil]).
    """
    import qrcode
    from qrcode.image.styledpil import StyledPilImage

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(image_factory=StyledPilImage)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


class DjangoEmailSender(EmailSender):
    """Concrete implementation backed by Django's email backend (SMTP)."""

    def send(self, *, subject: str, recipient: str, template: str, context: dict) -> int:
        from django.core.mail import EmailMultiAlternatives

        html_body = render_to_string(template, context)
        msg = EmailMultiAlternatives(
            subject=subject,
            body="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        msg.attach_alternative(html_body, "text/html")
        return msg.send(fail_silently=False)

    def send_ticket(self, *, registration) -> int:
        qr_data_uri = _generate_qr_base64(registration.qr_code)
        return self.send(
            subject=f"Your ticket — {registration.ticket_tier.event.title}",
            recipient=registration.attendee.user.email,
            template="emails/ticket.html",
            context={
                "registration": registration,
                "event": registration.ticket_tier.event,
                "tier": registration.ticket_tier,
                "attendee": registration.attendee,
                "qr_data_uri": qr_data_uri,
            },
        )


class ResendEmailSender(EmailSender):
    """Concrete implementation backed by the Resend API."""

    def send(self, *, subject: str, recipient: str, template: str, context: dict) -> int:
        import resend

        resend.api_key = settings.RESEND_API_KEY
        html_body = render_to_string(template, context)
        params: resend.Emails.SendParams = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [recipient],
            "subject": subject,
            "html": html_body,
        }
        resend.Emails.send(params)
        return 1

    def send_ticket(self, *, registration) -> int:
        qr_data_uri = _generate_qr_base64(registration.qr_code)
        return self.send(
            subject=f"Your ticket for {registration.ticket_tier.event.title} is confirmed!",
            recipient=registration.attendee.user.email,
            template="emails/ticket.html",
            context={
                "registration": registration,
                "event": registration.ticket_tier.event,
                "tier": registration.ticket_tier,
                "attendee": registration.attendee,
                "qr_data_uri": qr_data_uri,
            },
        )
