from django.contrib import admin

from .models import Event, Session, TicketTier


class SessionInline(admin.TabularInline):
    model = Session
    extra = 0


class TicketTierInline(admin.TabularInline):
    model = TicketTier
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "organizer", "status", "start_time", "end_time", "venue", "capacity"]
    list_filter = ["status"]
    search_fields = ["title", "venue", "organizer__organisation_name"]
    raw_id_fields = ["organizer"]
    readonly_fields = ["status"]
    date_hierarchy = "start_time"
    inlines = [SessionInline, TicketTierInline]
    actions = ["publish_events", "cancel_events"]

    @admin.action(description="Publish selected events")
    def publish_events(self, request, queryset):
        for event in queryset:
            event.publish()

    @admin.action(description="Cancel selected events")
    def cancel_events(self, request, queryset):
        for event in queryset:
            event.cancel()


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["title", "event", "speaker", "start_time", "duration_minutes"]
    search_fields = ["title", "speaker", "event__title"]
    raw_id_fields = ["event"]


@admin.register(TicketTier)
class TicketTierAdmin(admin.ModelAdmin):
    list_display = ["tier_name", "event", "price", "quantity_total", "quantity_sold"]
    search_fields = ["tier_name", "event__title"]
    raw_id_fields = ["event"]
