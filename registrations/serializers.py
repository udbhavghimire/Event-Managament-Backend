from rest_framework import serializers

from events.models import Event, TicketTier
from .models import CheckIn, Feedback, Payment, Refund, Registration


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = [
            "id",
            "attendee_id",
            "ticket_tier_id",
            "status",
            "qr_code",
            "registered_at",
        ]
        read_only_fields = fields


class MyRegistrationSerializer(serializers.ModelSerializer):
    """Registration with nested event/tier details for the attendee's My Events view."""

    event = serializers.SerializerMethodField()
    ticket_tier = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_refund = serializers.SerializerMethodField()

    class Meta:
        model = Registration
        fields = [
            "id",
            "status",
            "qr_code",
            "registered_at",
            "event",
            "ticket_tier",
            "payment",
            "can_cancel",
            "can_refund",
        ]
        read_only_fields = fields

    def get_event(self, obj: Registration) -> dict:
        e = obj.ticket_tier.event
        return {
            "id": e.id,
            "title": e.title,
            "venue": e.venue,
            "start_time": e.start_time,
            "end_time": e.end_time,
            "status": e.status,
        }

    def get_ticket_tier(self, obj: Registration) -> dict:
        t = obj.ticket_tier
        return {
            "id": t.id,
            "tier_name": t.tier_name,
            "price": str(t.price),
        }

    def get_payment(self, obj: Registration) -> dict | None:
        try:
            p = obj.payment
        except Payment.DoesNotExist:
            return None
        return {
            "amount": str(p.amount),
            "status": p.status,
            "paid_at": p.paid_at,
        }

    def get_can_cancel(self, obj: Registration) -> bool:
        if obj.status in (
            Registration.Status.CANCELLED,
            Registration.Status.REFUNDED,
            Registration.Status.REFUND_PENDING,
        ):
            return False
        if obj.status == Registration.Status.PENDING:
            return True
        if obj.status == Registration.Status.CONFIRMED:
            return _is_free_registration(obj)
        return False

    def get_can_refund(self, obj: Registration) -> bool:
        if obj.status != Registration.Status.CONFIRMED:
            return False
        if not _is_paid_registration(obj):
            return False
        return not obj.refunds.filter(status=Refund.Status.PENDING).exists()


def _is_free_registration(registration: Registration) -> bool:
    try:
        payment = registration.payment
    except Payment.DoesNotExist:
        return True
    return payment.gateway_ref == "FREE" or payment.amount == 0


def _is_paid_registration(registration: Registration) -> bool:
    try:
        payment = registration.payment
    except Payment.DoesNotExist:
        return False
    if payment.status == Payment.Status.REFUNDED:
        return False
    return payment.gateway_ref != "FREE" and payment.amount > 0


class RegistrationCreateSerializer(serializers.Serializer):
    ticket_tier_id = serializers.PrimaryKeyRelatedField(
        queryset=TicketTier.objects.select_related("event"),
        source="ticket_tier",
    )

    def validate(self, attrs: dict) -> dict:
        tier: TicketTier = attrs["ticket_tier"]
        if tier.event.status != Event.Status.PUBLISHED:
            raise serializers.ValidationError(
                {"ticket_tier_id": "This event is not currently accepting registrations."}
            )
        if tier.quantity_sold >= tier.quantity_total:
            raise serializers.ValidationError(
                {"ticket_tier_id": "No tickets remaining for this tier."}
            )
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "registration_id", "amount", "gateway_ref", "status", "paid_at"]
        read_only_fields = fields


class CheckInSerializer(serializers.Serializer):
    """Accepts the raw QR token string scanned from the attendee's ticket."""
    qr_token = serializers.CharField(max_length=64)


class FeedbackSerializer(serializers.ModelSerializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Feedback
        fields = ["id", "registration_id", "rating", "comment", "submitted_at"]
        read_only_fields = ["id", "submitted_at"]

    def validate_registration_id(self, value):
        """Ownership check: only the attendee of this registration can submit feedback."""
        request = self.context.get("request")
        if request and not value.attendee.user == request.user:
            raise serializers.ValidationError("You can only submit feedback for your own registrations.")
        return value


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = [
            "id",
            "registration_id",
            "amount",
            "gateway_ref",
            "reason",
            "status",
            "requested_at",
            "refunded_at",
        ]
        read_only_fields = fields


class RefundCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)
