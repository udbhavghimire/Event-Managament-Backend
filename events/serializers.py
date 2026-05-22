import os

from django.conf import settings
from rest_framework import serializers

from registrations.models import Registration

from .models import Event, Session, TicketTier


def build_media_url(file_field, request) -> str | None:
    """Return an absolute URL for a FileField, or None if empty."""
    if not file_field:
        return None
    url = file_field.url
    if request is not None:
        return request.build_absolute_uri(url)
    base = getattr(settings, "API_BASE_URL", "").rstrip("/")
    if base:
        return f"{base}{url}"
    return url


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
    registrations_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "organizer",
            "title",
            "description",
            "venue",
            "start_time",
            "end_time",
            "created_at",
            "status",
            "capacity",
            "registrations_count",
            "ticket_tiers",
            "image_url",
        ]

    def get_image_url(self, obj: Event) -> str | None:
        """Low-res thumbnail for list/card views."""
        request = self.context.get("request")
        thumb = obj.image_thumbnail if obj.image_thumbnail else obj.image
        return build_media_url(thumb, request)

    def get_registrations_count(self, obj: Event) -> int:
        """Active registrations only (excludes refunded and cancelled)."""
        return Registration.objects.filter(
            ticket_tier__event=obj,
            status__in=(
                Registration.Status.CONFIRMED,
                Registration.Status.REFUND_PENDING,
            ),
        ).count()

    def get_ticket_tiers(self, obj: Event) -> dict | None:
        """Return only the cheapest tier for list views."""
        tier = obj.ticket_tiers.order_by("price").first()
        if tier is None:
            return None
        return {
            "tier_name": tier.tier_name,
            "price": str(tier.price),
            "quantity_sold": tier.quantity_sold,
            "quantity_remaining": tier.quantity_total - tier.quantity_sold,
        }


class EventDetailSerializer(serializers.ModelSerializer):
    sessions = SessionSerializer(many=True, read_only=True)
    ticket_tiers = TicketTierSerializer(many=True, read_only=True)
    registrations_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    image_thumbnail_url = serializers.SerializerMethodField()

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
            "registrations_count",
            "sessions",
            "ticket_tiers",
            "image_url",
            "image_thumbnail_url",
        ]

    def get_image_url(self, obj: Event) -> str | None:
        """Full-resolution image for detail views."""
        request = self.context.get("request")
        return build_media_url(obj.image, request)

    def get_image_thumbnail_url(self, obj: Event) -> str | None:
        request = self.context.get("request")
        thumb = obj.image_thumbnail if obj.image_thumbnail else obj.image
        return build_media_url(thumb, request)

    def get_registrations_count(self, obj: Event) -> int:
        return Registration.objects.filter(
            ticket_tier__event=obj,
            status__in=(
                Registration.Status.CONFIRMED,
                Registration.Status.REFUND_PENDING,
            ),
        ).count()


class EventCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

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
            "image",
        ]
        read_only_fields = ["id"]

    def validate_image(self, value):
        if value is None:
            return value
        max_bytes = 5 * 1024 * 1024
        if value.size > max_bytes:
            raise serializers.ValidationError("Image must be 5 MB or smaller.")
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise serializers.ValidationError("Image must be JPEG, PNG, or WebP.")
        return value

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

    def create(self, validated_data):
        from .image_utils import generate_event_thumbnail

        instance = super().create(validated_data)
        if instance.image:
            generate_event_thumbnail(instance)
            instance.save(update_fields=["image_thumbnail"])
        return instance

    def update(self, instance, validated_data):
        from .image_utils import generate_event_thumbnail

        image_updated = "image" in validated_data
        instance = super().update(instance, validated_data)
        if image_updated and instance.image:
            generate_event_thumbnail(instance)
            instance.save(update_fields=["image_thumbnail"])
        return instance
