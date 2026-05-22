"""Image processing and database-backed storage for event photos."""
from io import BytesIO

from PIL import Image

THUMBNAIL_MAX_WIDTH = 480
THUMBNAIL_JPEG_QUALITY = 78


def generate_thumbnail_bytes(image_bytes: bytes) -> bytes:
    """Return a JPEG thumbnail (max width 480px) from raw image bytes."""
    img = Image.open(BytesIO(image_bytes))
    img = img.convert("RGB")

    if img.width > THUMBNAIL_MAX_WIDTH:
        ratio = THUMBNAIL_MAX_WIDTH / img.width
        new_size = (THUMBNAIL_MAX_WIDTH, max(1, int(img.height * ratio)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=THUMBNAIL_JPEG_QUALITY, optimize=True)
    return buffer.getvalue()
