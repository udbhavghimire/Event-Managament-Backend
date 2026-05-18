from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOrganizer(BasePermission):
    """Allow access only to users with role ORGANIZER."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.role == "ORGANIZER")


class IsAttendee(BasePermission):
    """Allow access only to users with role ATTENDEE."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.role == "ATTENDEE")


class IsAdmin(BasePermission):
    """Allow access only to users with role ADMIN."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.role == "ADMIN")


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission.
    Grants access when the requesting user owns the object or has the ADMIN role.

    The object must expose one of:
      • obj.user        (Organizer / Attendee profile)
      • obj.attendee.user  (Registration / Payment / CheckIn / Feedback)
      • obj             (User itself)
    """

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        if request.user.role == "ADMIN":
            return True

        # Direct user ownership
        if hasattr(obj, "user"):
            return obj.user == request.user

        # Registration-style models linked through attendee
        if hasattr(obj, "attendee"):
            return obj.attendee.user == request.user

        # The object itself is the user
        if obj == request.user:
            return True

        return False
