"""Persist uploaded event images in the database (survives Render ephemeral disk)."""
import mimetypes

from .image_utils import generate_thumbnail_bytes
from .models import Event


def persist_event_images(event: Event) -> None:
    """
    Copy the uploaded ImageField into PostgreSQL so images survive redeploys.
    Falls back silently if the file is missing on disk.
    """
    if not event.image:
        return

    try:
        event.image.open("rb")
        full_bytes = event.image.read()
    except (FileNotFoundError, OSError):
        return
    finally:
        try:
            event.image.close()
        except Exception:
            pass

    if not full_bytes:
        return

    mime = mimetypes.guess_type(event.image.name)[0] or "image/jpeg"
    thumb_bytes = generate_thumbnail_bytes(full_bytes)

    Event.objects.filter(pk=event.pk).update(
        image_data=full_bytes,
        image_mime_type=mime,
        image_thumbnail_data=thumb_bytes,
        image_thumbnail_mime_type="image/jpeg",
    )
    event.image_data = full_bytes
    event.image_mime_type = mime
    event.image_thumbnail_data = thumb_bytes
    event.image_thumbnail_mime_type = "image/jpeg"
