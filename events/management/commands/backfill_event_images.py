"""Copy on-disk event images into the database (run once after deploying image storage fix)."""
from django.core.management.base import BaseCommand

from events.image_storage import persist_event_images
from events.models import Event


class Command(BaseCommand):
    help = "Store existing event image files in the database (for Render / ephemeral disks)."

    def handle(self, *args, **options):
        qs = Event.objects.exclude(image="").exclude(image__isnull=True)
        ok = 0
        for event in qs:
            if event.has_stored_image:
                self.stdout.write(f"Skip event {event.pk} (already in DB)")
                continue
            before = event.has_stored_image
            persist_event_images(event)
            event.refresh_from_db()
            if event.has_stored_image and not before:
                ok += 1
                self.stdout.write(self.style.SUCCESS(f"Backfilled event {event.pk}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"Could not read file for event {event.pk} — re-upload the image")
                )
        self.stdout.write(self.style.SUCCESS(f"Done. Backfilled {ok} event(s)."))
