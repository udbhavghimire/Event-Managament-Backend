"""
Payment adapter — abstract interface + stub implementation for dev/tests.
Swap PaymentGateway for a Stripe or PayPal concrete class in production.
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
            amount=Decimal("0.00"),  # amount resolved from registration in service layer
        )
