from django.urls import path
from .views import (
    EventCancelView,
    EventDetailView,
    EventListCreateView,
    EventPublishView,
    SessionCreateView,
    SessionDetailView,
    TicketTierCreateView,
    TicketTierDetailView,
)

app_name = "events"

# All mounted at /api/ — patterns carry their full resource prefix.
urlpatterns = [
    # Events
    path("events/", EventListCreateView.as_view(), name="event_list_create"),
    path("events/<int:pk>/", EventDetailView.as_view(), name="event_detail"),
    path("events/<int:pk>/publish/", EventPublishView.as_view(), name="event_publish"),
    path("events/<int:pk>/cancel/", EventCancelView.as_view(), name="event_cancel"),

    # Sessions — nested create + top-level detail
    path("events/<int:event_id>/sessions/", SessionCreateView.as_view(), name="session_create"),
    path("sessions/<int:pk>/", SessionDetailView.as_view(), name="session_detail"),

    # Ticket tiers — nested create + top-level detail
    path("events/<int:event_id>/tiers/", TicketTierCreateView.as_view(), name="tier_create"),
    path("tiers/<int:pk>/", TicketTierDetailView.as_view(), name="tier_detail"),
]
