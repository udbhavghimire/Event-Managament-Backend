from django.urls import path
from .payment_views import PaymentConfigView
from .views import (
    CheckInView,
    FeedbackCreateView,
    MyRegistrationsView,
    RegistrationCancelView,
    RegistrationConfirmView,
    RegistrationCreateView,
    RegistrationRefundApproveView,
    RegistrationRefundRejectView,
    RegistrationRefundRequestView,
)

app_name = "registrations"

# All mounted at /api/ — patterns carry their full resource prefix.
urlpatterns = [
    path("payments/config/", PaymentConfigView.as_view(), name="payment_config"),
    path("registrations/", RegistrationCreateView.as_view(), name="registration_create"),
    path("registrations/<int:pk>/confirm/", RegistrationConfirmView.as_view(), name="registration_confirm"),
    path("registrations/<int:pk>/cancel/", RegistrationCancelView.as_view(), name="registration_cancel"),
    path("registrations/<int:pk>/refund/", RegistrationRefundRequestView.as_view(), name="registration_refund"),
    path(
        "registrations/<int:pk>/refund/approve/",
        RegistrationRefundApproveView.as_view(),
        name="registration_refund_approve",
    ),
    path(
        "registrations/<int:pk>/refund/reject/",
        RegistrationRefundRejectView.as_view(),
        name="registration_refund_reject",
    ),
    path("me/registrations/", MyRegistrationsView.as_view(), name="my_registrations"),
    path("checkins/", CheckInView.as_view(), name="check_in"),
    path("feedback/", FeedbackCreateView.as_view(), name="feedback_create"),
]
