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

# Content-ID referenced in templates/emails/ticket.html as cid:qr-code
QR_INLINE_CONTENT_ID = "qr-code"


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


def _generate_qr_png(data: str) -> bytes:
    """Render *data* as a QR code PNG and return raw bytes."""
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
    return buffer.read()


def _ticket_context(registration) -> dict:
    return {
        "registration": registration,
        "event": registration.ticket_tier.event,
        "tier": registration.ticket_tier,
        "attendee": registration.attendee,
        "qr_cid": QR_INLINE_CONTENT_ID,
    }


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
        from email.mime.image import MIMEImage

        from django.core.mail import EmailMultiAlternatives

        png_bytes = _generate_qr_png(registration.qr_code)
        html_body = render_to_string("emails/ticket.html", _ticket_context(registration))
        msg = EmailMultiAlternatives(
            subject=f"Your ticket — {registration.ticket_tier.event.title}",
            body="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[registration.attendee.user.email],
        )
        msg.attach_alternative(html_body, "text/html")
        inline = MIMEImage(png_bytes, _subtype="png")
        inline.add_header("Content-ID", f"<{QR_INLINE_CONTENT_ID}>")
        inline.add_header("Content-Disposition", "inline", filename="qr-code.png")
        msg.attach(inline)
        return msg.send(fail_silently=False)


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
        import resend

        resend.api_key = settings.RESEND_API_KEY
        png_bytes = _generate_qr_png(registration.qr_code)
        html_body = render_to_string("emails/ticket.html", _ticket_context(registration))
        params: resend.Emails.SendParams = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [registration.attendee.user.email],
            "subject": f"Your ticket for {registration.ticket_tier.event.title} is confirmed!",
            "html": html_body,
            "attachments": [
                {
                    "filename": "qr-code.png",
                    "content": base64.b64encode(png_bytes).decode("ascii"),
                    "content_id": QR_INLINE_CONTENT_ID,
                }
            ],
        }
        resend.Emails.send(params)
        return 1
