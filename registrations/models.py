from django.db import models


class Registration(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"

    attendee = models.ForeignKey(
        "accounts.Attendee",
        on_delete=models.PROTECT,
        related_name="registrations",
    )
    ticket_tier = models.ForeignKey(
        "events.TicketTier",
        on_delete=models.PROTECT,
        related_name="registrations",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    qr_code = models.CharField(max_length=64, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "registrations_registration"
        indexes = [
            models.Index(fields=["attendee"], name="idx_registration_attendee"),
        ]

    def __str__(self) -> str:
        return f"{self.attendee} — {self.ticket_tier} [{self.status}]"

    def confirm(self) -> None:
        self.status = self.Status.CONFIRMED
        self.save(update_fields=["status"])

    def cancel(self) -> None:
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status"])


class Payment(models.Model):
    class Status(models.TextChoices):
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    registration = models.OneToOneField(
        Registration,
        on_delete=models.CASCADE,
        related_name="payment",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gateway_ref = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "registrations_payment"

    def __str__(self) -> str:
        return f"Payment {self.gateway_ref} [{self.status}]"


class CheckIn(models.Model):
    class Method(models.TextChoices):
        QR_SCAN = "QR_SCAN", "QR Scan"
        MANUAL = "MANUAL", "Manual"

    registration = models.OneToOneField(
        Registration,
        on_delete=models.CASCADE,
        related_name="check_in",
    )
    checked_in_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.QR_SCAN)

    class Meta:
        db_table = "registrations_check_in"

    def __str__(self) -> str:
        return f"CheckIn for {self.registration} via {self.method}"


class Feedback(models.Model):
    registration = models.OneToOneField(
        Registration,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "registrations_feedback"

    def __str__(self) -> str:
        return f"Feedback for {self.registration} — {self.rating}★"
