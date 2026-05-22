"""Generate thumbnails when an event image is saved via admin or other non-API paths."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .image_utils import generate_event_thumbnail
from .models import Event


@receiver(post_save, sender=Event)
def create_event_thumbnail(sender, instance: Event, **kwargs) -> None:
    if kwargs.get("update_fields") == ["image_thumbnail"]:
        return
    if not instance.image:
        return
    generate_event_thumbnail(instance)
    if instance.image_thumbnail:
        Event.objects.filter(pk=instance.pk).update(
            image_thumbnail=instance.image_thumbnail.name
        )
