from rest_framework import serializers

from .models import Event, Session, TicketTier


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ["id", "event_id", "title", "speaker", "start_time", "duration_minutes"]
        read_only_fields = ["id", "event_id"]


class TicketTierSerializer(serializers.ModelSerializer):
    quantity_remaining = serializers.SerializerMethodField()

    class Meta:
        model = TicketTier
        fields = [
            "id",
            "event_id",
            "tier_name",
            "price",
            "quantity_total",
            "quantity_sold",
            "quantity_remaining",
        ]
        read_only_fields = ["id", "event_id", "quantity_sold", "quantity_remaining"]

    def get_quantity_remaining(self, obj: TicketTier) -> int:
        return obj.quantity_total - obj.quantity_sold


class EventListSerializer(serializers.ModelSerializer):
    ticket_tiers = serializers.SerializerMethodField()
    organizer = serializers.CharField(source="organizer.organisation_name", read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "organizer",
            "title",
            "venue",
            "start_time",
            "end_time",
            "status",
            "capacity",
            "ticket_tiers",
        ]

    def get_ticket_tiers(self, obj: Event) -> dict | None:
        """Return only the cheapest tier for list views."""
        tier = obj.ticket_tiers.order_by("price").first()
        if tier is None:
            return None
        return {
            "tier_name": tier.tier_name,
            "price": str(tier.price),
            "quantity_remaining": tier.quantity_total - tier.quantity_sold,
        }


class EventDetailSerializer(serializers.ModelSerializer):
    sessions = SessionSerializer(many=True, read_only=True)
    ticket_tiers = TicketTierSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "organizer_id",
            "title",
            "description",
            "venue",
            "start_time",
            "end_time",
            "capacity",
            "status",
            "sessions",
            "ticket_tiers",
        ]


class EventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "venue",
            "start_time",
            "end_time",
            "capacity",
            "status",
        ]
        read_only_fields = ["id"]

    def validate_capacity(self, value: int) -> int:
        if value < 1:
            raise serializers.ValidationError("Capacity must be at least 1.")
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs.get("end_time") and attrs.get("start_time"):
            if attrs["end_time"] <= attrs["start_time"]:
                raise serializers.ValidationError(
                    {"end_time": "end_time must be after start_time."}
                )
        return attrs
