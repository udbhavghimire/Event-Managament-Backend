from django.urls import path
from .views import (
    AdminSuspendUserView,
    AdminUserListView,
    LoginView,
    LogoutView,
    RefreshView,
    RegisterView,
)

app_name = "accounts"

# Mounted at /api/auth/
urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
]

# Mounted at /api/ → resolves to /api/admin/users/ etc.
admin_urlpatterns = [
    path("admin/users/", AdminUserListView.as_view(), name="admin_user_list"),
    path("admin/users/<int:pk>/suspend/", AdminSuspendUserView.as_view(), name="admin_user_suspend"),
]
