from pathlib import Path

from django.apps import AppConfig
from django.conf import settings


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "events"
    verbose_name = "Events"

    def ready(self) -> None:
        Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
        from . import signals  # noqa: F401
