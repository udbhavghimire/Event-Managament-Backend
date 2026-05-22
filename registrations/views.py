from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.adapters.payment_adapter import get_payment_gateway
from core.permissions import IsAttendee, IsOrganizer, IsAdmin
from core.services.registration_service import RegisterForEventService, SoldOutError

from .models import CheckIn, Feedback, Registration
from .serializers import (
    CheckInSerializer,
    FeedbackSerializer,
    MyRegistrationSerializer,
    RegistrationCreateSerializer,
    RegistrationSerializer,
    RefundCreateSerializer,
    RefundSerializer,
    _is_free_registration,
    _is_paid_registration,
)


def _err(code: str, detail: str, http_status) -> Response:
    """Uniform error response format used throughout registrations."""
    return Response({"error": code, "detail": detail}, status=http_status)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegistrationCreateView(APIView):
    permission_classes = [IsAttendee]

    def post(self, request) -> Response:
        serializer = RegistrationCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        tier = serializer.validated_data["ticket_tier"]

        try:
            if tier.price == 0:
                # Free path — confirm immediately
                service = RegisterForEventService()
                registration = service.execute(
                    attendee=request.user.attendee, ticket_tier=tier
                )
                return Response(
                    RegistrationSerializer(registration).data,
                    status=status.HTTP_201_CREATED,
                )
            else:
                # Paid path — create PENDING, return payment intent
                registration = Registration.objects.create(
                    attendee=request.user.attendee,
                    ticket_tier=tier,
                    status=Registration.Status.PENDING,
                )
                gateway = get_payment_gateway()
                intent = gateway.create_intent(
                    amount=tier.price,
                    currency="AUD",
                    registration_id=registration.pk,
                )
                return Response(
                    {
                        "registration_id": registration.pk,
                        "client_secret": intent.client_secret,
                        "payment_intent_id": intent.intent_id,
                    },
                    status=status.HTTP_201_CREATED,
                )
        except SoldOutError as exc:
            return _err("sold_out", str(exc), status.HTTP_409_CONFLICT)


class RegistrationConfirmView(APIView):
    permission_classes = [IsAttendee]

    def post(self, request, pk: int) -> Response:
        registration = get_object_or_404(
            Registration, pk=pk, attendee__user=request.user
        )
        if registration.status != Registration.Status.PENDING:
            return _err(
                "registration_not_pending",
                "Only PENDING registrations can be confirmed.",
                status.HTTP_400_BAD_REQUEST,
            )

        intent_id = request.data.get("intent_id", "")
        gateway = get_payment_gateway()
        verification = gateway.verify_intent(intent_id=intent_id)

        if not verification.success:
            return _err(
                "payment_failed",
                verification.error or "Payment verification failed.",
                status.HTTP_402_PAYMENT_REQUIRED,
            )

        try:
            service = RegisterForEventService()
            registration = service.confirm(
                registration=registration,
                gateway_ref=verification.gateway_ref,
            )
        except SoldOutError as exc:
            return _err("sold_out", str(exc), status.HTTP_409_CONFLICT)

        return Response(RegistrationSerializer(registration).data, status=status.HTTP_200_OK)


class RegistrationCancelView(APIView):
    permission_classes = [IsAttendee]

    def post(self, request, pk: int) -> Response:
        registration = get_object_or_404(
            Registration.objects.select_related("ticket_tier", "payment"),
            pk=pk,
            attendee__user=request.user,
        )
        if registration.status in (
            Registration.Status.CANCELLED,
            Registration.Status.REFUNDED,
        ):
            return _err(
                "cannot_cancel",
                "This registration can no longer be cancelled.",
                status.HTTP_400_BAD_REQUEST,
            )
        if registration.status == Registration.Status.CONFIRMED and _is_paid_registration(
            registration
        ):
            return _err(
                "use_refund",
                "Paid registrations cannot be cancelled. Request a refund instead.",
                status.HTTP_400_BAD_REQUEST,
            )
        if registration.status == Registration.Status.CONFIRMED:
            from events.models import TicketTier

            TicketTier.objects.filter(pk=registration.ticket_tier_id).update(
                quantity_sold=F("quantity_sold") - 1
            )
        registration.cancel()
        return Response(MyRegistrationSerializer(registration).data)


class MyRegistrationsView(APIView):
    permission_classes = [IsAttendee]

    def get(self, request) -> Response:
        registrations = (
            Registration.objects.filter(attendee__user=request.user)
            .select_related("ticket_tier__event")
            .prefetch_related("payment")
            .order_by("-registered_at")
        )
        return Response(MyRegistrationSerializer(registrations, many=True).data)


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------

class RegistrationRefundView(APIView):
    """
    Refund a confirmed paid registration.
    Attendees may refund their own ticket; organizers may refund any ticket on their event.
    POST /api/registrations/<pk>/refund/  { "reason": "..." }
    """
    permission_classes = [IsAttendee | IsOrganizer | IsAdmin]

    def post(self, request, pk: int) -> Response:
        registration = get_object_or_404(
            Registration.objects.select_related(
                "ticket_tier__event__organizer__user", "payment"
            ),
            pk=pk,
        )

        role = request.user.role
        if role == "ATTENDEE":
            if registration.attendee.user != request.user:
                return _err(
                    "permission_denied",
                    "You can only refund your own registrations.",
                    status.HTTP_403_FORBIDDEN,
                )
            if registration.status != Registration.Status.CONFIRMED:
                return _err(
                    "refund_not_allowed",
                    "Only confirmed registrations can be refunded.",
                    status.HTTP_400_BAD_REQUEST,
                )
            if not _is_paid_registration(registration):
                return _err(
                    "refund_not_allowed",
                    "Free registrations do not require a refund.",
                    status.HTTP_400_BAD_REQUEST,
                )
        elif role != "ADMIN" and registration.ticket_tier.event.organizer.user != request.user:
            return _err("permission_denied", "You do not own this event.", status.HTTP_403_FORBIDDEN)

        serializer = RefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            service = RegisterForEventService()
            registration = service.refund(
                registration=registration,
                reason=serializer.validated_data["reason"],
            )
        except ValueError as exc:
            return _err("refund_not_allowed", str(exc), status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return _err("gateway_error", str(exc), status.HTTP_502_BAD_GATEWAY)

        refund = registration.refunds.order_by("-refunded_at").first()
        return Response(RefundSerializer(refund).data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Check-in
# ---------------------------------------------------------------------------

class CheckInView(APIView):
    permission_classes = [IsOrganizer | IsAdmin]

    def post(self, request) -> Response:
        serializer = CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qr_token = serializer.validated_data["qr_token"]

        try:
            registration = Registration.objects.select_related(
                "attendee__user", "check_in"
            ).get(qr_code=qr_token)
        except Registration.DoesNotExist:
            return _err("invalid_qr", "QR token not found.", status.HTTP_404_NOT_FOUND)

        if registration.status != Registration.Status.CONFIRMED:
            return _err(
                "registration_not_confirmed",
                "This ticket has not been confirmed.",
                status.HTTP_410_GONE,
            )

        if hasattr(registration, "check_in"):
            return _err(
                "already_checked_in",
                "This ticket has already been scanned.",
                status.HTTP_409_CONFLICT,
            )

        CheckIn.objects.create(registration=registration)
        return Response(
            {"detail": "Check-in successful.", "attendee": registration.attendee.user.full_name},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

class FeedbackCreateView(APIView):
    permission_classes = [IsAttendee]

    def post(self, request) -> Response:
        serializer = FeedbackSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        registration = serializer.validated_data["registration_id"]  # FK object

        # Must have checked in
        if not hasattr(registration, "check_in"):
            return _err(
                "not_checked_in",
                "You must have checked in before leaving feedback.",
                status.HTTP_400_BAD_REQUEST,
            )

        # Event must have ended within the last 14 days
        event = registration.ticket_tier.event
        days_since_end = (timezone.now() - event.end_time).days
        if days_since_end < 0:
            return _err(
                "event_not_ended",
                "The event has not ended yet.",
                status.HTTP_400_BAD_REQUEST,
            )
        if days_since_end > 14:
            return _err(
                "feedback_window_closed",
                "The 14-day feedback window has closed.",
                status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicate feedback (model has OneToOneField)
        if hasattr(registration, "feedback"):
            return _err(
                "feedback_already_submitted",
                "You have already submitted feedback for this registration.",
                status.HTTP_409_CONFLICT,
            )

        feedback = serializer.save()
        return Response(FeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED)
