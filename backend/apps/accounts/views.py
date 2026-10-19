"""
Accounts API views: auth, me, invites, roles, members.
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import Invitation, Membership, Role
from apps.accounts.serializers import (
    AcceptInvitationSerializer,
    ForgotPasswordSerializer,
    HireFluxTokenObtainPairSerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
    MeSerializer,
    MembershipSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    RoleSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from apps.accounts.services import (
    accept_invitation,
    create_and_send_invitation,
    request_password_reset,
    reset_password,
    verify_email,
)
from apps.core.mixins import OrgQuerysetMixin
from apps.core.models import AuditLog
from apps.core.audit import log_action
from apps.core.permissions import (
    HasPerm,
    IsOrgMember,
    IsStaffUser,
    PERMISSION_CATALOG,
    STAFF_PERSONAS,
)
from apps.organizations.serializers import OrganizationSerializer

User = get_user_model()


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = HireFluxTokenObtainPairSerializer
    org_optional = True

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code != 200:
            log_action(
                request=request,
                action=AuditLog.Action.LOGIN,
                resource_type="User",
                message="User logged in",
            )
        return response


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    org_optional = True


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    org_optional = True

    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                token = RefreshToken(refresh)
                token.blacklist()
            except Exception:  # noqa: BLE001
                pass
        log_action(
            request=request,
            action=AuditLog.Action.LOGOUT,
            resource_type="User",
            resource_id=str(request.user.pk),
            message="User logged out",
        )
        return Response({"success": True})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    org_optional = True

    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        user = result["user"]
        org = result["organization"]
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "data": {
                    "user": UserSerializer(user).data,
                    "organization": OrganizationSerializer(org).data,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    org_optional = True

    def get(self, request):
        return Response(
            {
                "success": True,
                "data": MeSerializer(request.user, context={"request": request}).data,
            }
        )

    def patch(self, request):
        serializer = UserSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": MeSerializer(request.user).data})


class RoleViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "GET": ["users.roles"],
        "SAFE": ["users.view"],
        "POST": ["users.view"],
        "PUT": ["users.roles"],
        "PATCH": ["users.roles"],
        "DELETE": ["users.roles"],
    }
    queryset = Role.objects.all()
    search_fields = ["name", "slug"]
    filterset_fields = ["is_system", "is_active"]
    ordering = ["name"]

    def perform_create(self, serializer):
        org = self.get_organization()
        serializer.save(organization=org, is_system=False)

    def perform_destroy(self, instance):
        if not instance.is_system:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("System roles cannot be deleted.")
        instance.delete()

    @action(detail=False, methods=["get"], url_path="catalog")
    def catalog(self, request):
        return Response(
            {
                "success": True,
                "data": {
                    "permissions": PERMISSION_CATALOG,
                    "personas": {
                        key: {
                            "label": meta["label"],
                            "description": meta.get("description", ""),
                            "permissions": meta.get("permissions") or [],
                        }
                        for key, meta in STAFF_PERSONAS.items()
                    },
                },
            }
        )


class MembershipViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "GET": ["users.view"],
        "SAFE": ["users.view"],
        "PUT": ["users.edit"],
        "PATCH": ["users.edit"],
        "DELETE": ["users.view"],
    }
    http_method_names = ["get", "patch", "put", "delete", "head", "options"]
    queryset = Membership.objects.select_related("user", "role", "organization")
    search_fields = ["user__email", "user__first_name", "user__last_name", "title"]
    filterset_fields = ["role", "is_active", "is_owner"]
    ordering = ["joined_at"]

    def perform_destroy(self, instance):
        if instance.is_owner:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Cannot remove the organization owner.")
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class InvitationViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "GET": ["users.view"],
        "SAFE": ["users.view"],
        "POST": ["users.invite"],
        "DELETE": ["users.invite"],
    }
    http_method_names = ["get", "post", "delete", "head", "options"]
    queryset = Invitation.objects.select_related("role", "invited_by", "organization")
    filterset_fields = ["status", "email", "role"]
    search_fields = ["email"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return InvitationCreateSerializer
        return InvitationSerializer

    def create(self, request, *args, **kwargs):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = self.get_organization()
        role = None
        role_id = serializer.validated_data.get("role_id")
        if role_id:
            role = Role.objects.filter(pk=role_id, organization=org).first()
            if not role:
                return Response(
                    {
                        "success": False,
                        "error": {"code": "invalid_role", "message": "Role not found."},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            invitation = create_and_send_invitation(
                organization=org,
                email=serializer.validated_data["email"],
                role=role,
                invited_by=request.user,
                message=serializer.validated_data.get("message", ""),
                request=request,
            )
        except ValueError as exc:
            return Response(
                {
                    "success": False,
                    "error": {"code": "invite_error", "message": str(exc)},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "success": True,
                "data": InvitationSerializer(invitation).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def perform_destroy(self, instance):
        instance.status = Invitation.Status.REVOKED
        instance.save(update_fields=["status", "updated_at"])


class AcceptInviteView(APIView):
    permission_classes = [AllowAny]
    org_optional = True

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, membership, invitation = accept_invitation(
                token=serializer.validated_data["token"],
                password=serializer.validated_data.get("password") or None,
                first_name=serializer.validated_data.get("first_name", ""),
                last_name=serializer.validated_data.get("last_name", ""),
                user=request.user if request.user.is_authenticated else None,
                request=request,
            )
        except ValueError as exc:
            return Response(
                {
                    "success": False,
                    "error": {"code": "accept_failed", "message": str(exc)},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "data": {
                    "user": UserSerializer(user).data,
                    "membership": MembershipSerializer(membership).data,
                    "invitation": InvitationSerializer(invitation).data,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            }
        )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    org_optional = True

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(
            email=serializer.validated_data["email"],
            request=request,
        )
        # Always succeed to avoid email enumeration
        return Response(
            {
                "success": True,
                "message": "If an account exists for that email, a reset link has been sent.",
            }
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    org_optional = True

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reset_password(
                token=serializer.validated_data["token"],
                new_password=serializer.validated_data["password"],
                request=request,
            )
        except ValueError as exc:
            return Response(
                {
                    "success": False,
                    "error": {"code": "reset_failed", "message": str(exc)},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"success": True, "message": "Password has been reset."})


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    org_optional = True

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = verify_email(
                token=serializer.validated_data["token"],
                request=request,
            )
        except ValueError as exc:
            return Response(
                {
                    "success": False,
                    "error": {"code": "verify_failed", "message": str(exc)},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "success": True,
                "data": UserSerializer(user).data,
            }
        )
