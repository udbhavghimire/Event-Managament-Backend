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
        fields = ["id", "registration_id", "amount", "gateway_ref", "reason", "refunded_at"]
        read_only_fields = fields


class RefundCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)
