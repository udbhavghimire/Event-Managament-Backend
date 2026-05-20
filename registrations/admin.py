from django.contrib import admin

from .models import CheckIn, Feedback, Payment, Refund, Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ["id", "attendee", "ticket_tier", "status", "registered_at"]
    list_filter = ["status"]
    search_fields = ["attendee__user__email", "ticket_tier__event__title", "qr_code"]
    raw_id_fields = ["attendee", "ticket_tier"]
    readonly_fields = ["registered_at"]
    actions = ["confirm_registrations", "cancel_registrations"]

    @admin.action(description="Confirm selected registrations")
    def confirm_registrations(self, request, queryset):
        for reg in queryset:
            reg.confirm()

    @admin.action(description="Cancel selected registrations")
    def cancel_registrations(self, request, queryset):
        for reg in queryset:
            reg.cancel()


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["registration", "amount", "gateway_ref", "status", "paid_at"]
    list_filter = ["status"]
    search_fields = ["gateway_ref", "registration__attendee__user__email"]
    raw_id_fields = ["registration"]
    readonly_fields = ["paid_at"]


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ["registration", "method", "checked_in_at"]
    list_filter = ["method"]
    search_fields = ["registration__attendee__user__email"]
    raw_id_fields = ["registration"]
    readonly_fields = ["checked_in_at"]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["registration", "rating", "submitted_at"]
    list_filter = ["rating"]
    search_fields = ["registration__attendee__user__email"]
    raw_id_fields = ["registration"]
    readonly_fields = ["submitted_at"]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ["id", "registration", "amount", "gateway_ref", "refunded_at"]
    search_fields = ["gateway_ref", "registration__attendee__user__email"]
    raw_id_fields = ["registration"]
    readonly_fields = ["refunded_at"]
