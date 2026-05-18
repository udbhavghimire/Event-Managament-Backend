from django.urls import path
from .views import AttendeeCSVExportView, EventAnalyticsView

app_name = "analytics"

# Mounted at /api/ → resolves to /api/events/{pk}/analytics/ etc.
urlpatterns = [
    path("events/<int:pk>/analytics/", EventAnalyticsView.as_view(), name="event_analytics"),
    path("events/<int:pk>/attendees.csv", AttendeeCSVExportView.as_view(), name="attendee_csv"),
]
