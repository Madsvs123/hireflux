"""
Integration ViewSets: provider gallery, connections, configs, webhooks,
deliveries, API keys, and the public inbound webhook receiver.
"""
import json

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.integrations import services
from apps.integrations.models import (
    ApiKey,
    IntegrationConfig,
    IntegrationConnection,
    IntegrationProvider,
    WebhookDelivery,
    WebhookEndpoint,
)
from apps.integrations.serializers import (
    ApiKeySerializer,
    ConnectionConnectSerializer,
    IntegrationConfigSerializer,
    IntegrationConnectionSerializer,
    IntegrationProviderSerializer,
    WebhookDeliverySerializer,
    WebhookEndpointSerializer,
    WebhookEventSerializer,
)


class IntegrationProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """Global provider catalog (org-visible, not org-scoped)."""

    queryset = IntegrationProvider.objects.filter(is_active=True)
    serializer_class = IntegrationProviderSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["integrations.view"]}
    filterset_fields = ["category", "auth_type"]
    search_fields = ["key", "name", "description"]
    ordering = ["name"]


class IntegrationConnectionViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = IntegrationConnection.objects.select_related("provider")
    serializer_class = IntegrationConnectionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["integrations.view"],
        "POST": ["integrations.manage"],
        "PUT": ["integrations.manage"],
        "PATCH": ["integrations.manage"],
        "DELETE": ["integrations.manage"],
    }
    filterset_fields = ["provider", "status"]
    search_fields = ["name", "provider__name", "provider__key"]
    ordering = ["name"]
    audit_resource_type = "IntegrationConnection"

    def get_permissions(self):
        action_perms = {
            "connect": ["integrations.manage"],
            "disconnect": ["integrations.manage"],
            "test": ["integrations.manage"],
            "sync": ["integrations.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def connect(self, request, pk=None):
        """Connect an existing connection (OAuth2 URL or immediate)."""
        connection = self.get_object()
        ser = ConnectionConnectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = services.connect_connection(
            connection,
            actor=request.user,
            redirect_uri=ser.validated_data.get("redirect_uri", ""),
            code=ser.validated_data.get("code", ""),
        )
        return Response(result)

    @action(detail=True, methods=["post"])
    def disconnect(self, request, pk=None):
        connection = self.get_object()
        connection = services.disconnect_connection(connection, actor=request.user)
        return Response(IntegrationConnectionSerializer(connection).data)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Run a live health check against the provider."""
        connection = self.get_object()
        ok, message = services.test_connection(connection)
        connection.status = (
            IntegrationConnection.Status.CONNECTED
            if ok
            else IntegrationConnection.Status.ERROR
        )
        connection.last_error = "" if ok else message
        connection.save(update_fields=["status", "last_error", "updated_at"])
        return Response(
            {
                "ok": ok,
                "message": message,
                "status": connection.status,
            },
            status=status.HTTP_200_OK if ok else status.HTTP_502_BAD_GATEWAY,
        )

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """Health-check and record a sync timestamp."""
        connection = self.get_object()
        connection = services.sync_connection(connection, actor=request.user)
        return Response(IntegrationConnectionSerializer(connection).data)


class IntegrationConfigViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = IntegrationConfig.objects.select_related("connection")
    serializer_class = IntegrationConfigSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["integrations.view"],
        "POST": ["integrations.manage"],
        "PUT": ["integrations.manage"],
        "PATCH": ["integrations.manage"],
        "DELETE": ["integrations.manage"],
    }
    filterset_fields = ["connection", "is_secret"]
    search_fields = ["key"]
    ordering = ["key"]
    audit_resource_type = "IntegrationConfig"


class WebhookEndpointViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = WebhookEndpoint.objects.all()
    serializer_class = WebhookEndpointSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["integrations.view"],
        "POST": ["integrations.manage"],
        "PUT": ["integrations.manage"],
        "PATCH": ["integrations.manage"],
        "DELETE": ["integrations.manage"],
    }
    filterset_fields = ["is_active"]
    search_fields = ["name", "url"]
    ordering = ["name"]
    audit_resource_type = "WebhookEndpoint"

    def get_permissions(self):
        action_perms = {
            "rotate_secret": ["integrations.manage"],
            "fire_event": ["integrations.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        endpoint, secret = services.create_webhook_endpoint(
            organization=request.organization,
            name=serializer.validated_data["name"],
            url=serializer.validated_data["url"],
            events=serializer.validated_data.get("events", []),
            is_active=serializer.validated_data.get("is_active", True),
            secret=serializer.validated_data.get("secret"),
            actor=request.user,
        )
        serializer.instance = endpoint
        data = serializer.data
        data["secret"] = secret
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="rotate-secret")
    def rotate_secret(self, request, pk=None):
        """Generate a new signing secret (returned once)."""
        endpoint = self.get_object()
        endpoint, secret = services.rotate_webhook_secret(endpoint, actor=request.user)
        return Response({"id": str(endpoint.pk), "secret": secret})

    @action(detail=False, methods=["post"], url_path="fire-event")
    def fire_event(self, request):
        """Manually fire an event at subscribed endpoints."""
        ser = WebhookEventSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        deliveries = services.dispatch_webhook_event(
            organization=request.organization,
            event=ser.validated_data["event"],
            payload=ser.validated_data.get("payload", {}),
            endpoint_id=ser.validated_data.get("endpoint_id"),
            actor=request.user,
        )
        return Response(
            {
                "queued": len(deliveries),
                "delivery_ids": [str(d.pk) for d in deliveries],
            },
            status=status.HTTP_202_ACCEPTED,
        )


class WebhookDeliveryViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = WebhookDelivery.objects.select_related("endpoint")
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["integrations.view"]}
    filterset_fields = ["endpoint", "event", "status"]
    search_fields = ["event", "response_body"]
    ordering = ["-created_at"]

    def get_permissions(self):
        action_perms = {
            "redeliver": ["integrations.manage"],
            "retry_failed": ["integrations.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def redeliver(self, request, pk=None):
        """Re-enqueue a single delivery."""
        delivery = self.get_object()
        delivery = services.redeliver_delivery(delivery, actor=request.user)
        return Response(WebhookDeliverySerializer(delivery).data)

    @action(detail=False, methods=["post"], url_path="retry-failed")
    def retry_failed(self, request):
        """Re-enqueue every failed delivery for the organization."""
        count = services.retry_failed_deliveries(
            organization=request.organization, actor=request.user
        )
        return Response({"queued": count}, status=status.HTTP_202_ACCEPTED)


class ApiKeyViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = ApiKey.objects.all()
    serializer_class = ApiKeySerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["integrations.view"],
        "POST": ["integrations.manage"],
        "PUT": ["integrations.manage"],
        "PATCH": ["integrations.manage"],
        "DELETE": ["integrations.manage"],
    }
    filterset_fields = ["is_active"]
    search_fields = ["name", "key_prefix"]
    ordering = ["-created_at"]
    audit_resource_type = "ApiKey"

    def get_permissions(self):
        action_perms = {
            "regenerate": ["integrations.manage"],
            "revoke": ["integrations.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key, plaintext = services.create_api_key(
            organization=request.organization,
            name=serializer.validated_data["name"],
            scopes=serializer.validated_data.get("scopes", []),
            is_active=serializer.validated_data.get("is_active", True),
            expires_at=serializer.validated_data.get("expires_at"),
            actor=request.user,
        )
        serializer.instance = key
        data = serializer.data
        data["key"] = plaintext
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """Replace key material; the old key stops working immediately."""
        key = self.get_object()
        key, plaintext = services.regenerate_api_key(key, actor=request.user)
        serializer = self.get_serializer(key)
        data = serializer.data
        data["key"] = plaintext
        return Response(data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        """Revoke a key immediately."""
        key = self.get_object()
        key = services.revoke_api_key(key, actor=request.user)
        return Response(self.get_serializer(key).data)


class ProviderWebhookReceiver(APIView):
    """
    Public inbound endpoint for provider callbacks.

    Intentionally unauthenticated; delivery is idempotent and recorded on
    the matching webhook endpoint. Rate limiting / IP allow-listing should
    be applied at the gateway in production.
    """

    permission_classes = []
    authentication_classes = []
    org_optional = True

    def post(self, request, provider_key):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            payload = {}
        headers = {k.lower(): v for k, v in request.headers.items()}
        from apps.integrations.tasks import process_provider_webhook

        process_provider_webhook.delay(
            provider_key,
            payload,
            headers,
            request.build_absolute_uri(),
        )
        return Response({"ok": True, "provider": provider_key}, status=status.HTTP_202_ACCEPTED)
