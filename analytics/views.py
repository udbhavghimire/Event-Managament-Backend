import csv
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsOrganizer
from events.models import Event
from registrations.models import CheckIn, Feedback, Registration


def _get_owned_event(request, pk: int) -> Event:
    """Fetch an event and assert the requesting user is its organizer."""
    event = get_object_or_404(Event, pk=pk)
    if event.organizer.user != request.user:
        raise PermissionDenied("You do not own this event.")
    return event


class EventAnalyticsView(APIView):
    permission_classes = [IsOrganizer]

    def get(self, request, pk: int) -> Response:
        event = _get_owned_event(request, pk)

        confirmed_regs = Registration.objects.filter(
            ticket_tier__event=event,
            status=Registration.Status.CONFIRMED,
        )

        tickets_sold: int = confirmed_regs.count()

        revenue: Decimal = (
            confirmed_regs.aggregate(total=Sum("ticket_tier__price"))["total"]
            or Decimal("0.00")
        )

        check_in_count: int = CheckIn.objects.filter(
            registration__ticket_tier__event=event
        ).count()
        check_in_rate: float = (
            round(check_in_count / tickets_sold, 4) if tickets_sold > 0 else 0.0
        )

        avg_rating = (
            Feedback.objects.filter(
                registration__ticket_tier__event=event
            ).aggregate(avg=Avg("rating"))["avg"]
        )
        average_rating: float | None = round(float(avg_rating), 2) if avg_rating else None

        tier_rows = (
            confirmed_regs
            .values("ticket_tier__tier_name", "ticket_tier__price")
            .annotate(count=Count("id"))
            .order_by("ticket_tier__tier_name")
        )
        registrations_by_tier = [
            {
                "tier_name": row["ticket_tier__tier_name"],
                "count": row["count"],
                "revenue": str(
                    Decimal(str(row["ticket_tier__price"])) * row["count"]
                ),
            }
            for row in tier_rows
        ]

        return Response(
            {
                "tickets_sold": tickets_sold,
                "revenue": str(revenue),
                "check_in_rate": check_in_rate,
                "average_rating": average_rating,
                "registrations_by_tier": registrations_by_tier,
            }
        )


class AttendeeCSVExportView(APIView):
    permission_classes = [IsOrganizer]

    def get(self, request, pk: int) -> HttpResponse:
        event = _get_owned_event(request, pk)

        registrations = (
            Registration.objects
            .filter(ticket_tier__event=event)
            .select_related("attendee__user", "ticket_tier")
            .prefetch_related("check_in")
            .order_by("registered_at")
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="event_{event.pk}_attendees.csv"'
        )

        writer = csv.writer(response)
        writer.writerow([
            "registration_id",
            "attendee_name",
            "attendee_email",
            "tier_name",
            "registered_at",
            "checked_in",
        ])

        for reg in registrations:
            checked_in = "yes" if hasattr(reg, "check_in") else "no"
            writer.writerow([
                reg.pk,
                reg.attendee.user.full_name,
                reg.attendee.user.email,
                reg.ticket_tier.tier_name,
                reg.registered_at.strftime("%Y-%m-%d %H:%M:%S"),
                checked_in,
            ])

        return response
