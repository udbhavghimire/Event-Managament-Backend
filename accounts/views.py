import os

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import filters, generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core.permissions import IsAdmin
from .models import User
from .serializers import AdminUserSerializer, LoginSerializer, RegisterSerializer, UserSerializer

REFRESH_COOKIE = "refresh_token"
COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def _user_payload(user: User) -> dict:
    return UserSerializer(user).data


def _get_refresh_token(request: Request) -> str | None:
    """Refresh token from HttpOnly cookie (direct API) or JSON body (BFF proxy)."""
    return request.COOKIES.get(REFRESH_COOKIE) or request.data.get("refresh")


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/")


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                "user": _user_payload(user),
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )
        _set_refresh_cookie(response, str(refresh))
        return response


@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=True),
    name="post",
)
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                "user": _user_payload(user),
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )
        _set_refresh_cookie(response, str(refresh))
        return response


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(_user_payload(request.user))


class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        from .models import User as _User

        raw_token = _get_refresh_token(request)
        if not raw_token:
            return Response(
                {"detail": "Refresh token not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            old_refresh = RefreshToken(raw_token)

            # Blacklist the incoming token before issuing a new one
            old_refresh.blacklist()

            # Issue a fresh token pair for the same user
            user = _User.objects.get(pk=old_refresh["user_id"])
            new_refresh = RefreshToken.for_user(user)

            response = Response(
                {"access": str(new_refresh.access_token)},
                status=status.HTTP_200_OK,
            )
            _set_refresh_cookie(response, str(new_refresh))
            return response

        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        raw_token = _get_refresh_token(request)
        if raw_token:
            try:
                token = RefreshToken(raw_token)
                token.blacklist()
            except TokenError:
                pass  # already invalid — still clear the cookie

        response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        _clear_refresh_cookie(response)
        return response


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------

class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all().order_by("-created_at")
    filter_backends = [filters.SearchFilter]
    search_fields = ["email"]


class AdminSuspendUserView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request: Request, pk: int) -> Response:
        user = get_object_or_404(User, pk=pk)
        if not user.is_active:
            return Response(
                {"detail": f"{user.email} is already suspended."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(
            {"detail": f"{user.email} has been suspended."},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# One-time superuser bootstrap endpoint
# ---------------------------------------------------------------------------

class CreateSuperAdminView(APIView):
    """
    One-time endpoint to create the first superuser/admin account.

    Protected by SETUP_TOKEN env var — disable by deleting that env var on Render.
    Anyone who knows the token can call this, so delete it immediately after use.

    POST /api/setup/create-admin/
    Headers: X-Setup-Token: <your SETUP_TOKEN value>
    Body: { "email": "...", "password": "...", "full_name": "..." }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        setup_token = os.environ.get("SETUP_TOKEN", "")
        if not setup_token:
            return Response(
                {"detail": "Setup endpoint is disabled. Set SETUP_TOKEN env var to enable it."},
                status=status.HTTP_403_FORBIDDEN,
            )

        provided_token = request.headers.get("X-Setup-Token", "")
        if provided_token != setup_token:
            return Response(
                {"detail": "Invalid setup token."},
                status=status.HTTP_403_FORBIDDEN,
            )

        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")
        full_name = request.data.get("full_name", "Admin").strip()

        if not email or not password:
            return Response(
                {"detail": "email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(password) < 8:
            return Response(
                {"detail": "Password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": f"A user with email {email} already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        user = User.objects.create_superuser(
            email=email,
            password=password,
            full_name=full_name,
            role=User.Role.ADMIN,
        )

        return Response(
            {
                "detail": "Superuser created successfully. Remove SETUP_TOKEN from env vars now.",
                "user_id": user.pk,
                "email": user.email,
                "role": user.role,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            },
            status=status.HTTP_201_CREATED,
        )
