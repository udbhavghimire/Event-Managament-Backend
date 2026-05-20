"""
Stripe webhook handler.

Endpoint: POST /api/webhooks/stripe/

Stripe calls this after every payment event. The view:
  1. Verifies the Stripe-Signature header to reject forged requests.
  2. Handles payment_intent.succeeded → confirms the registration.
  3. Handles payment_intent.payment_failed → marks the registration CANCELLED.

Configure your Stripe dashboard webhook to send at minimum:
  - payment_intent.succeeded
  - payment_intent.payment_failed
"""
import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.services.registration_service import RegisterForEventService, SoldOutError

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    try:
        import stripe
        stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")

        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            # No secret configured (dev only) — parse the raw payload without verification
            logger.warning("STRIPE_WEBHOOK_SECRET is not set; skipping signature verification.")
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)

    except ValueError:
        logger.error("Stripe webhook: invalid JSON payload.")
        return HttpResponse("Invalid payload.", status=400)
    except stripe.errors.SignatureVerificationError:
        logger.error("Stripe webhook: invalid signature.")
        return HttpResponse("Invalid signature.", status=400)

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "payment_intent.succeeded":
        _handle_payment_intent_succeeded(data_object)
    elif event_type == "payment_intent.payment_failed":
        _handle_payment_intent_failed(data_object)
    else:
        logger.debug("Stripe webhook: unhandled event type '%s'.", event_type)

    return HttpResponse("ok", status=200)


def _handle_payment_intent_succeeded(intent: dict) -> None:
    """
    Confirm the registration associated with the PaymentIntent.
    The registration_id is stored in the intent's metadata at creation time.
    """
    from registrations.models import Registration

    registration_id = (intent.get("metadata") or {}).get("registration_id")
    if not registration_id:
        logger.warning(
            "payment_intent.succeeded: no registration_id in metadata for intent %s",
            intent.get("id"),
        )
        return

    try:
        registration = Registration.objects.select_related(
            "ticket_tier", "attendee__user"
        ).get(pk=int(registration_id))
    except (Registration.DoesNotExist, ValueError):
        logger.error(
            "payment_intent.succeeded: registration %s not found.", registration_id
        )
        return

    if registration.status != Registration.Status.PENDING:
        # Already confirmed (e.g. via the client-side confirm endpoint) — idempotent.
        logger.info(
            "payment_intent.succeeded: registration %s already in status %s; skipping.",
            registration_id,
            registration.status,
        )
        return

    try:
        service = RegisterForEventService()
        service.confirm(
            registration=registration,
            gateway_ref=intent["id"],
        )
        logger.info(
            "payment_intent.succeeded: registration %s confirmed via webhook.", registration_id
        )
    except SoldOutError as exc:
        logger.error(
            "payment_intent.succeeded: sold-out error for registration %s: %s",
            registration_id,
            exc,
        )
    except Exception as exc:
        logger.exception(
            "payment_intent.succeeded: unexpected error for registration %s: %s",
            registration_id,
            exc,
        )


def _handle_payment_intent_failed(intent: dict) -> None:
    """Cancel the PENDING registration when payment definitively fails."""
    from registrations.models import Registration

    registration_id = (intent.get("metadata") or {}).get("registration_id")
    if not registration_id:
        return

    try:
        registration = Registration.objects.get(
            pk=int(registration_id), status=Registration.Status.PENDING
        )
        registration.cancel()
        logger.info(
            "payment_intent.payment_failed: registration %s cancelled.", registration_id
        )
    except (Registration.DoesNotExist, ValueError):
        pass
