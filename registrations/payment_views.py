from django.conf import settings
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView


class PaymentConfigView(APIView):
    """
    Public Stripe config for the frontend (publishable key only).
    GET /api/payments/config/
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request) -> Response:
        gateway = getattr(settings, "PAYMENT_GATEWAY", "stub").lower()
        publishable_key = getattr(settings, "STRIPE_PUBLISHABLE_KEY", "")
        return Response(
            {
                "payment_gateway": gateway,
                "publishable_key": publishable_key,
                "stripe_enabled": gateway == "stripe" and bool(publishable_key),
                "currency": "aud",
            }
        )
