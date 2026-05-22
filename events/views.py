from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, generics, mixins, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsOrganizer

from .filters import EventFilter
from .models import Event, Session, TicketTier
from .serializers import (
    EventCreateSerializer,
    EventDetailSerializer,
    EventListSerializer,
    SessionSerializer,
    TicketTierSerializer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class EventOwnershipMixin:
    """Mixin that resolves an event and enforces organizer ownership."""

    def get_owned_event(self, event_id: int) -> Event:
        event = get_object_or_404(Event, pk=event_id)
        if event.organizer.user != self.request.user:
            raise PermissionDenied("You do not own this event.")
        return event


# ---------------------------------------------------------------------------
# Event views
# ---------------------------------------------------------------------------

class EventListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EventFilter
    search_fields = ["title", "description"]
    ordering_fields = ["start_time", "created_at"]
    ordering = ["start_time"]

    def get_queryset(self):
        mine = self.request.query_params.get("mine") == "true"

        if mine:
            return (
                Event.objects
                .filter(organizer=self.request.user.organizer)
                .select_related("organizer")
                .prefetch_related("ticket_tiers")
            )

        qs = Event.objects.filter(
            status=Event.Status.PUBLISHED,
            start_time__gte=timezone.now(),
        ).select_related("organizer").prefetch_related("ticket_tiers")

        from_date = self.request.query_params.get("from")
        if from_date:
            qs = qs.filter(start_time__date__gte=from_date)
        return qs

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsOrganizer()]
        if self.request.query_params.get("mine") == "true":
            return [IsOrganizer()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EventCreateSerializer
        return EventListSerializer

    def perform_create(self, serializer):
        event = serializer.save(organizer=self.request.user.organizer)
        if not event.ticket_tiers.exists():
            TicketTier.objects.create(
                event=event,
                tier_name="Free",
                price=0,
                quantity_total=event.capacity,
            )


class EventDetailView(generics.RetrieveUpdateAPIView):
    queryset = Event.objects.select_related("organizer").prefetch_related("sessions", "ticket_tiers")
    lookup_field = "pk"
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [IsOrganizer()]

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return EventDetailSerializer
        return EventCreateSerializer

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in permissions.SAFE_METHODS:
            if obj.organizer.user != request.user:
                raise PermissionDenied("You do not own this event.")


class EventPublishView(EventOwnershipMixin, APIView):
    permission_classes = [IsOrganizer]

    def post(self, request, pk: int) -> Response:
        event = self.get_owned_event(pk)
        event.publish()
        return Response({"detail": "Event published.", "status": event.status})


class EventUnpublishView(EventOwnershipMixin, APIView):
    permission_classes = [IsOrganizer]

    def post(self, request, pk: int) -> Response:
        event = self.get_owned_event(pk)
        if event.status != Event.Status.PUBLISHED:
            return Response(
                {"error": "event_not_published", "detail": "Only published events can be unpublished."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        event.unpublish()
        return Response({"detail": "Event unpublished.", "status": event.status})


class EventCancelView(EventOwnershipMixin, APIView):
    permission_classes = [IsOrganizer]

    def post(self, request, pk: int) -> Response:
        event = self.get_owned_event(pk)
        event.cancel()
        return Response({"detail": "Event cancelled.", "status": event.status})


# ---------------------------------------------------------------------------
# Session views
# ---------------------------------------------------------------------------

class SessionCreateView(EventOwnershipMixin, generics.CreateAPIView):
    serializer_class = SessionSerializer
    permission_classes = [IsOrganizer]

    def perform_create(self, serializer):
        event = self.get_owned_event(self.kwargs["event_id"])
        serializer.save(event=event)


class SessionDetailView(
    EventOwnershipMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    queryset = Session.objects.select_related("event__organizer")
    serializer_class = SessionSerializer
    permission_classes = [IsOrganizer]

    def _check_ownership(self):
        session = self.get_object()
        if session.event.organizer.user != self.request.user:
            raise PermissionDenied("You do not own this session's event.")
        return session

    def patch(self, request, *args, **kwargs):
        self._check_ownership()
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self._check_ownership()
        return self.destroy(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Ticket tier views
# ---------------------------------------------------------------------------

class TicketTierCreateView(EventOwnershipMixin, generics.CreateAPIView):
    serializer_class = TicketTierSerializer
    permission_classes = [IsOrganizer]

    def perform_create(self, serializer):
        event = self.get_owned_event(self.kwargs["event_id"])
        serializer.save(event=event)


class TicketTierDetailView(
    EventOwnershipMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    queryset = TicketTier.objects.select_related("event__organizer")
    serializer_class = TicketTierSerializer
    permission_classes = [IsOrganizer]

    def _check_ownership(self):
        tier = self.get_object()
        if tier.event.organizer.user != self.request.user:
            raise PermissionDenied("You do not own this tier's event.")
        return tier

    def patch(self, request, *args, **kwargs):
        self._check_ownership()
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        tier = self._check_ownership()
        if tier.quantity_sold > 0:
            return Response(
                {
                    "error": "tier_has_sales",
                    "detail": "Cannot delete a tier that already has sold tickets.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.destroy(request, *args, **kwargs)
