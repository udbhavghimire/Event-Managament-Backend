from django.db import models


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        CANCELLED = "CANCELLED", "Cancelled"

    organizer = models.ForeignKey(
        "accounts.Organizer",
        on_delete=models.CASCADE,
        related_name="events",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    venue = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        db_table = "events_event"
        indexes = [
            models.Index(fields=["status"], name="idx_event_status"),
        ]

    def __str__(self) -> str:
        return self.title

    def publish(self) -> None:
        self.status = self.Status.PUBLISHED
        self.save(update_fields=["status"])

    def cancel(self) -> None:
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status"])

    @property
    def is_sold_out(self) -> bool:
        """True when every ticket tier is fully sold out."""
        tiers = self.ticket_tiers.all()
        if not tiers.exists():
            return False
        return not tiers.filter(quantity_sold__lt=models.F("quantity_total")).exists()


class Session(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="sessions")
    title = models.CharField(max_length=255)
    speaker = models.CharField(max_length=255, null=True, blank=True)
    start_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()

    class Meta:
        db_table = "events_session"

    def __str__(self) -> str:
        return f"{self.event} — {self.title}"


class TicketTier(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_tiers")
    tier_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_total = models.PositiveIntegerField()
    quantity_sold = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "events_ticket_tier"

    def __str__(self) -> str:
        return f"{self.event} — {self.tier_name}"
