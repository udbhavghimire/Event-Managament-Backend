from django.contrib import admin as django_admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from accounts.urls import admin_urlpatterns

urlpatterns = [
    path("admin/", django_admin.site.urls),

    # Auth endpoints  → /api/auth/register/, /api/auth/login/, etc.
    path("api/auth/", include("accounts.urls", namespace="accounts")),

    # Admin endpoints → /api/admin/users/, /api/admin/users/{id}/suspend/
    path("api/", include((admin_urlpatterns, "admin_api"))),

    # Events, sessions, tiers  → /api/events/, /api/sessions/{id}/, etc.
    path("api/", include("events.urls", namespace="events")),

    # Registrations, check-in, feedback, me
    path("api/", include("registrations.urls", namespace="registrations")),

    # Analytics → /api/events/{id}/analytics/, /api/events/{id}/attendees.csv
    path("api/", include("analytics.urls", namespace="analytics")),

    # OpenAPI docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger_ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
