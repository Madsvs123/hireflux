from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    AcceptInviteView,
    ForgotPasswordView,
    InvitationViewSet,
    LoginView,
    LogoutView,
    MeView,
    MembershipViewSet,
    RefreshView,
    RegisterView,
    ResetPasswordView,
    RoleViewSet,
    VerifyEmailView,
)

router = DefaultRouter()
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"members", MembershipViewSet, basename="member")
router.register(r"invitations", InvitationViewSet, basename="invitation")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LoginView.as_view(), name="auth-logout"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/forgot-password/", ResetPasswordView.as_view(), name="auth-forgot-password"),
    path("auth/reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("auth/accept-invite/", AcceptInviteView.as_view(), name="auth-accept-invite"),
    path("", include(router.urls)),
]
