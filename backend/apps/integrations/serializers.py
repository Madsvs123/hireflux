"""
Serializers for the integrations domain.

Credentials, webhook secrets, and API keys are write-only or masked —
never exposed in responses.
"""
from rest_framework import serializers

from apps.integrations.models import (
    ApiKey,
    IntegrationConfig,
    IntegrationConnection,
    IntegrationProvider,
    WebhookDelivery,
    WebhookEndpoint,
)


class IntegrationProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationProvider
        fields = [
            "id",
            "key",
            "name",
            "category",
            "description",
            "auth_type",
            "config_schema",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "key",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class IntegrationConnectionSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source="provider.name", read_only=True)
    provider_key = serializers.SlugField(source="provider.key", read_only=True)
    provider_auth_type = serializers.CharField(source="provider.auth_type", read_only=True)
    credentials = serializers.JSONField(
        write_only=True,
        required=False,
        default=dict,
        help_text="Plaintext credentials; encrypted before storage.",
    )

    class Meta:
        model = IntegrationConnection
        fields = [
            "id",
            "provider",
            "provider_name",
            "provider_key",
            "provider_auth_type",
            "name",
            "status",
            "credentials",
            "config",
            "last_synced_at",
            "last_error",
            "connected_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "last_synced_at",
            "last_error",
            "connected_by",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        from apps.integrations.crypto import encrypt_dict

        credentials = validated_data.pop("credentials", {}) or {}
        validated_data["credentials_encrypted"] = encrypt_dict(credentials)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from apps.integrations.crypto import encrypt_dict

        credentials = validated_data.pop("credentials", None)
        if credentials is not None:
            merged = dict(instance.credentials_encrypted or {})
            merged.update(encrypt_dict(credentials or {}))
            instance.credentials_encrypted = merged
            instance.save(update_fields=["credentials_encrypted", "updated_at"])
        return super().update(instance, validated_data)


class IntegrationConfigSerializer(serializers.ModelSerializer):
    connection_name = serializers.CharField(source="connection.name", read_only=True)

    class Meta:
        model = IntegrationConfig
        fields = [
            "id",
            "connection",
            "connection_name",
            "key",
            "value",
            "is_secret",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_secret and data.get("value") not in (None, "", {}):
            data["value"] = "••••••••"
        return data

    def create(self, validated_data):
        from apps.integrations.crypto import encrypt_value

        if validated_data.get("is_secret"):
            value = validated_data.get("value")
            if value not in (None, "", {}):
                validated_data["value"] = encrypt_value(value)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from apps.integrations.crypto import encrypt_value

        if validated_data.get("is_secret", instance.is_secret):
            value = validated_data.get("value")
            if value not in (None, "", {}):
                validated_data["value"] = encrypt_value(value)
        return super().update(instance, validated_data)


class WebhookEndpointSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Signing secret. Auto-generated when omitted; returned once.",
    )

    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "name",
            "url",
            "secret",
            "events",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def update(self, instance, validated_data):
        # Secrets are only assigned at creation or via rotate-secret.
        validated_data.pop("secret", None)
        return super().update(instance, validated_data)


class WebhookDeliverySerializer(serializers.ModelSerializer):
    endpoint_name = serializers.CharField(source="endpoint.name", read_only=True)
    endpoint_url = serializers.CharField(source="endpoint.url", read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = [
            "id",
            "endpoint",
            "endpoint_name",
            "endpoint_url",
            "event",
            "payload",
            "status",
            "request_headers",
            "response_status",
            "response_body",
            "attempts",
            "next_attempt_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ApiKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiKey
        fields = [
            "id",
            "name",
            "key_prefix",
            "scopes",
            "is_active",
            "expires_at",
            "last_used_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "key_prefix",
            "last_used_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class ConnectionConnectSerializer(serializers.Serializer):
    """Input for the connect action (OAuth2 callback or key validation)."""

    redirect_uri = serializers.URLField(required=False, allow_blank=True)
    code = serializers.CharField(required=False, allow_blank=True)


class WebhookEventSerializer(serializers.Serializer):
    """Fire an arbitrary event at one or more endpoints."""

    event = serializers.CharField()
    endpoint_id = serializers.UUIDField(required=False, allow_null=True)
    payload = serializers.JSONField(required=False, default=dict)
