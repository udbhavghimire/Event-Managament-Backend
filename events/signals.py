"""Sync uploaded files into database storage after save."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .image_storage import persist_event_images
from .models import Event


@receiver(post_save, sender=Event)
def sync_event_images_to_database(sender, instance: Event, **kwargs) -> None:
    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        skip = {
            "image_data",
            "image_mime_type",
            "image_thumbnail_data",
            "image_thumbnail_mime_type",
            "image_thumbnail",
        }
        if set(update_fields) <= skip:
            return
    if instance.image:
        persist_event_images(instance)
