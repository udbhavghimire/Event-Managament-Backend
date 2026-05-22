"""Generate a low-resolution thumbnail when an event image is uploaded."""
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image

THUMBNAIL_MAX_WIDTH = 480
THUMBNAIL_JPEG_QUALITY = 78


def generate_event_thumbnail(event) -> None:
    """Resize event.image into event.image_thumbnail (JPEG, max width 480px)."""
    if not event.image:
        return

    event.image.open("rb")
    try:
        img = Image.open(event.image)
        img = img.convert("RGB")

        if img.width > THUMBNAIL_MAX_WIDTH:
            ratio = THUMBNAIL_MAX_WIDTH / img.width
            new_size = (THUMBNAIL_MAX_WIDTH, max(1, int(img.height * ratio)))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=THUMBNAIL_JPEG_QUALITY, optimize=True)
        buffer.seek(0)

        base_name = event.image.name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        thumb_name = f"{base_name}_thumb.jpg"

        if event.image_thumbnail:
            event.image_thumbnail.delete(save=False)

        event.image_thumbnail.save(thumb_name, ContentFile(buffer.read()), save=False)
    finally:
        event.image.close()
