"""
Payment adapter — abstract interface + concrete implementations.

Gateway selection:
  - Set PAYMENT_GATEWAY=stripe in settings (or env) to use Stripe.
  - Default is StubPaymentGateway (always succeeds) — for dev/tests.

Usage:
  from core.adapters.payment_adapter import get_payment_gateway
  gateway = get_payment_gateway()
"""
import abc
import uuid
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class PaymentResult:
    success: bool
    transaction_id: str
    amount: Decimal
    error: str = ""


@dataclass
class PaymentIntent:
    intent_id: str
    client_secret: str
    amount: Decimal


@dataclass
class PaymentVerification:
    success: bool
    gateway_ref: str
    amount: Decimal
    error: str = ""


class PaymentGateway(abc.ABC):
    """Abstract contract every payment provider must satisfy."""

    @abc.abstractmethod
    def charge(self, *, amount: Decimal, currency: str, token: str) -> PaymentResult:
        ...

    @abc.abstractmethod
    def refund(self, *, transaction_id: str, amount: Decimal) -> PaymentResult:
        ...

    @abc.abstractmethod
    def create_intent(
        self, *, amount: Decimal, currency: str, registration_id: int
    ) -> PaymentIntent:
        """Create a payment intent and return the client_secret for the frontend."""
        ...

    @abc.abstractmethod
    def verify_intent(self, *, intent_id: str) -> PaymentVerification:
        """Server-side verification of a payment intent — never trust the client."""
        ...


class StubPaymentGateway(PaymentGateway):
    """Always succeeds — use in tests and local dev."""

    def charge(self, *, amount: Decimal, currency: str, token: str) -> PaymentResult:
        return PaymentResult(
            success=True,
            transaction_id=str(uuid.uuid4()),
            amount=amount,
        )

    def refund(self, *, transaction_id: str, amount: Decimal) -> PaymentResult:
        return PaymentResult(
            success=True,
            transaction_id=transaction_id,
            amount=amount,
        )

    def create_intent(
        self, *, amount: Decimal, currency: str, registration_id: int
    ) -> PaymentIntent:
        return PaymentIntent(
            intent_id=f"stub_intent_{uuid.uuid4().hex[:12]}",
            client_secret=f"stub_secret_{uuid.uuid4().hex[:12]}",
            amount=amount,
        )

    def verify_intent(self, *, intent_id: str) -> PaymentVerification:
        return PaymentVerification(
            success=True,
            gateway_ref=intent_id,
            amount=Decimal("0.00"),
        )


class StripePaymentGateway(PaymentGateway):
    """Production Stripe gateway. Requires STRIPE_SECRET_KEY in settings."""

    def __init__(self, secret_key: str) -> None:
        import stripe as _stripe
        self._stripe = _stripe
        self._stripe.api_key = secret_key

    def charge(self, *, amount: Decimal, currency: str, token: str) -> PaymentResult:
        """Legacy charge via card token (Charges API). Prefer create_intent for SCA."""
        try:
            charge = self._stripe.Charge.create(
                amount=int(amount * 100),  # Stripe expects cents
                currency=currency.lower(),
                source=token,
            )
            return PaymentResult(
                success=charge["status"] == "succeeded",
                transaction_id=charge["id"],
                amount=Decimal(str(charge["amount"] / 100)),
            )
        except self._stripe.StripeError as exc:
            return PaymentResult(
                success=False,
                transaction_id="",
                amount=amount,
                error=str(exc),
            )

    def refund(self, *, transaction_id: str, amount: Decimal) -> PaymentResult:
        """Issue a full or partial refund against a PaymentIntent or Charge."""
        try:
            refund_obj = self._stripe.Refund.create(
                payment_intent=transaction_id,
                amount=int(amount * 100),
            )
            return PaymentResult(
                success=refund_obj["status"] == "succeeded",
                transaction_id=refund_obj["id"],
                amount=Decimal(str(refund_obj["amount"] / 100)),
            )
        except self._stripe.StripeError as exc:
            return PaymentResult(
                success=False,
                transaction_id=transaction_id,
                amount=amount,
                error=str(exc),
            )

    def create_intent(
        self, *, amount: Decimal, currency: str, registration_id: int
    ) -> PaymentIntent:
        """Create a PaymentIntent; the client uses client_secret to complete payment."""
        try:
            intent = self._stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency.lower(),
                metadata={"registration_id": str(registration_id)},
                automatic_payment_methods={"enabled": True},
            )
            return PaymentIntent(
                intent_id=intent["id"],
                client_secret=intent["client_secret"],
                amount=amount,
            )
        except self._stripe.StripeError as exc:
            raise RuntimeError(f"Stripe create_intent failed: {exc}") from exc

    def verify_intent(self, *, intent_id: str) -> PaymentVerification:
        """Fetch the PaymentIntent from Stripe and verify it succeeded."""
        try:
            intent = self._stripe.PaymentIntent.retrieve(intent_id)
            succeeded = intent["status"] == "succeeded"
            return PaymentVerification(
                success=succeeded,
                gateway_ref=intent_id,
                amount=Decimal(str(intent["amount"] / 100)),
                error="" if succeeded else f"Intent status: {intent['status']}",
            )
        except self._stripe.StripeError as exc:
            return PaymentVerification(
                success=False,
                gateway_ref=intent_id,
                amount=Decimal("0.00"),
                error=str(exc),
            )


def get_payment_gateway() -> PaymentGateway:
    """
    Factory: returns the configured gateway.
    Set PAYMENT_GATEWAY='stripe' and STRIPE_SECRET_KEY in settings/env for production.
    """
    from django.conf import settings

    gateway_name = getattr(settings, "PAYMENT_GATEWAY", "stub").lower()
    if gateway_name == "stripe":
        secret_key = getattr(settings, "STRIPE_SECRET_KEY", "")
        if not secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY must be set when PAYMENT_GATEWAY='stripe'.")
        return StripePaymentGateway(secret_key=secret_key)
    return StubPaymentGateway()
