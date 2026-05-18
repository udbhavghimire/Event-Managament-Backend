from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Attendee, Organizer, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-created_at"]
    list_display = ["email", "full_name", "role", "is_active", "is_staff", "created_at"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email", "full_name"]
    readonly_fields = ["created_at", "last_login", "date_joined"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at", "last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "role", "password1", "password2"),
        }),
    )
    # username is removed — clear the parent's filter
    filter_horizontal = ("groups", "user_permissions")


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ["user", "organisation_name", "contact_phone"]
    search_fields = ["organisation_name", "user__email"]
    raw_id_fields = ["user"]


@admin.register(Attendee)
class AttendeeAdmin(admin.ModelAdmin):
    list_display = ["user"]
    search_fields = ["user__email"]
    raw_id_fields = ["user"]
