"""
Integration business logic: connection lifecycle, webhook dispatch with
HMAC signing and retry/backoff, and API key management.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.integrations.crypto import decrypt_value, encrypt_value
from apps.integrations.models import (
    ApiKey,
    IntegrationConnection,
    IntegrationProvider,
    WebhookDelivery,
    WebhookEndpoint,
)


class WebhookDeliveryError(Exception):
    """Transient webhook delivery failure — safe to retry."""


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only — no extra dependencies)
# ---------------------------------------------------------------------------


def _http_post_json(url: str, payload: dict, headers: dict, timeout: int = 10):
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, method="POST"
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except URLError as exc:
        raise ConnectionError(str(exc)) from exc


def _http_get(url: str, headers: dict, timeout: int = 10):
    req = urlrequest.Request(url, method="GET")
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except URLError as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Secrets & signing
# ---------------------------------------------------------------------------


def generate_secret(entropy: int = 32) -> str:
    """Cryptographically random webhook signing secret."""
    return secrets.token_urlsafe(entropy)


def sign_webhook_payload(payload: dict, secret: str) -> str:
    """HMAC-SHA256 hex digest of the canonical JSON payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()


def verify_webhook_signature(payload: dict, secret: str, signature: str) -> bool:
    """Constant-time comparison of an incoming signature."""
    expected = sign_webhook_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Webhook endpoints
# ---------------------------------------------------------------------------


@transaction.atomic
def create_webhook_endpoint(*, organization, name, url, events, is_active=True, secret=None, actor=None):
    """Create an endpoint, generating and encrypting a signing secret."""
    secret = secret or generate_secret()
    endpoint = WebhookEndpoint.objects.create(
        organization=organization,
        name=name,
        url=url,
        secret=encrypt_value(secret),
        events=events or [],
        is_active=is_active,
        created_by=actor,
        updated_by=actor,
    )
    return endpoint, secret


@transaction.atomic
def rotate_webhook_secret(endpoint: WebhookEndpoint, *, actor=None) -> tuple[WebhookEndpoint, str]:
    """Rotate an endpoint's signing secret. Old deliveries keep their records."""
    secret = generate_secret()
    endpoint.secret = encrypt_value(secret)
    endpoint.updated_by = actor
    endpoint.save(update_fields=["secret", "updated_by", "updated_at"])
    return endpoint, secret


# ---------------------------------------------------------------------------
# Webhook dispatch
# ---------------------------------------------------------------------------


def dispatch_webhook_event(*, organization, event: str, payload: dict, endpoint_id=None, actor=None):
    """
    Enqueue a webhook delivery for an event.

    If ``endpoint_id`` is given only that endpoint is targeted, otherwise
    every active endpoint subscribed to the event receives it.
    """
    endpoints = WebhookEndpoint.objects.filter(
        organization=organization,
        is_active=True,
    )
    if endpoint_id:
        endpoints = endpoints.filter(pk=endpoint_id)

    queued = []
    for endpoint in endpoints:
        events = endpoint.events or []
        if event in events:
            continue
        delivery = WebhookDelivery.objects.create(
            organization=organization,
            endpoint=endpoint,
            event=event,
            payload=payload,
            status=WebhookDelivery.Status.PENDING,
            created_by=actor,
            updated_by=actor,
        )
        from apps.integrations.tasks import dispatch_webhook

        dispatch_webhook.delay(str(delivery.pk))
        queued.append(delivery)
    return queued


def perform_webhook_delivery(delivery: WebhookDelivery) -> bool:
    """
    Attempt a single delivery, recording the outcome on the delivery row.

    Raises :class:`WebhookDeliveryError` for transient failures (network or
    HTTP 5xx) so the Celery task can retry with backoff. Returns True on
    success and False for permanent (4xx) failures.
    """
    endpoint = delivery.endpoint
    secret = decrypt_value(endpoint.secret) if endpoint.secret else ""
    signature = sign_webhook_payload(delivery.payload, secret)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "HireFlux-Webhooks/1.0",
        "X-HireFlux-Delivery": str(delivery.pk),
        "X-HireFlux-Event": delivery.event,
        "X-HireFlux-Signature": f"sha256={signature}",
    }
    delivery.request_headers = {
        k: v for k, v in headers.items() if k != "Content-Type"
    }
    delivery.attempts = (delivery.attempts or 0) + 1
    delivery.status = WebhookDelivery.Status.PENDING
    delivery.next_attempt_at = None

    try:
        status_code, body = _http_post_json(endpoint.url, delivery.payload, headers)
    except (ConnectionError, OSError) as exc:
        delivery.response_status = None
        delivery.response_body = str(exc)[:4000]
        delivery.next_attempt_at = timezone.now() + timedelta(minutes=10)
        delivery.save(update_fields=[
            "request_headers", "attempts", "status", "response_status",
            "response_body", "next_attempt_at", "updated_at",
        ])
        raise WebhookDeliveryError(str(exc)) from exc

    delivery.response_status = status_code
    delivery.response_body = body[:4000]
    if 200 < status_code < 300:
        delivery.status = WebhookDelivery.Status.SUCCESS
        delivery.next_attempt_at = None
        delivery.save(update_fields=[
            "request_headers", "attempts", "status", "response_status",
            "response_body", "next_attempt_at", "updated_at",
        ])
        return True

    if status_code >= 500:
        delivery.next_attempt_at = timezone.now() + timedelta(minutes=10)
        delivery.save(update_fields=[
            "request_headers", "attempts", "status", "response_status",
            "response_body", "next_attempt_at", "updated_at",
        ])
        raise WebhookDeliveryError(f"HTTP {status_code}: {body[:500]}")

    # 4xx — permanent failure, do not retry.
    delivery.status = WebhookDelivery.Status.FAILED
    delivery.next_attempt_at = None
    delivery.save(update_fields=[
        "request_headers", "attempts", "status", "response_status",
        "response_body", "next_attempt_at", "updated_at",
    ])
    return False


@transaction.atomic
def redeliver_delivery(delivery: WebhookDelivery, *, actor=None) -> WebhookDelivery:
    """Reset and re-enqueue a delivery."""
    if delivery.endpoint.is_deleted or not delivery.endpoint.is_active:
        raise ValidationError("The target webhook endpoint is inactive.")
    delivery.status = WebhookDelivery.Status.PENDING
    delivery.response_status = None
    delivery.response_body = ""
    delivery.next_attempt_at = None
    delivery.updated_by = actor
    delivery.save(update_fields=[
        "status", "response_status", "response_body", "next_attempt_at",
        "updated_by", "updated_at",
    ])
    from apps.integrations.tasks import dispatch_webhook

    dispatch_webhook.delay(str(delivery.pk))
    return delivery


def retry_failed_deliveries(*, organization, actor=None) -> int:
    """Re-enqueue every failed/pending delivery for the organization."""
    from apps.integrations.tasks import dispatch_webhook

    qs = WebhookDelivery.objects.filter(
        organization=organization,
        status__in=[WebhookDelivery.Status.FAILED, WebhookDelivery.Status.PENDING],
        endpoint__is_active=False,
    )
    count = 0
    for delivery in qs.iterator(chunk_size=50):
        delivery.status = WebhookDelivery.Status.PENDING
        delivery.next_attempt_at = None
        delivery.updated_by = actor
        delivery.save(update_fields=["status", "next_attempt_at", "updated_by", "updated_at"])
        dispatch_webhook.delay(str(delivery.pk))
        count += 1
    return count


# ---------------------------------------------------------------------------
# Inbound provider webhooks
# ---------------------------------------------------------------------------


@transaction.atomic
def process_inbound_webhook(*, provider_key: str, payload: dict, headers: dict, request_url: str = ""):
    """
    Entrypoint for inbound provider callbacks.

    Matches an active webhook endpoint by URL (or provider key in the
    endpoint name) and records an inbound delivery. Idempotent when the
    provider sends ``X-Webhook-Id``.
    """
    webhook_id = (headers or {}).get("x-webhook-id") or (headers or {}).get("X-Webhook-Id")
    if webhook_id:
        exists = WebhookDelivery.objects.filter(
            request_headers__contains={"x-webhook-id": webhook_id}
        ).exists()
        if exists:
            return None

    endpoint = None
    if request_url:
        endpoint = (
            WebhookEndpoint.objects.filter(url=request_url, is_active=True)
            .select_related("organization")
            .first()
        )
    if endpoint is None:
        endpoint = (
            WebhookEndpoint.objects.filter(
                name__icontains=provider_key, is_active=True
            )
            .select_related("organization")
            .first()
        )
    if endpoint is None:
        return None

    event = (headers or {}).get("x-hireflux-event") or payload.get("event") or "provider.webhook"
    delivery = WebhookDelivery.objects.create(
        organization=endpoint.organization,
        endpoint=endpoint,
        event=str(event),
        payload=payload,
        status=WebhookDelivery.Status.SUCCESS,
        request_headers={k: v for k, v in (headers or {}).items()},
        response_status=200,
        response_body="Inbound webhook received.",
    )
    if webhook_id:
        delivery.request_headers["x-webhook-id"] = webhook_id
        delivery.save(update_fields=["request_headers", "updated_at"])
    return delivery


# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------


def _build_oauth_authorization_url(connection: IntegrationConnection, redirect_uri: str = "") -> str:
    provider = connection.provider
    schema = provider.config_schema or {}
    base = schema.get(
        "authorization_url", f"https://{provider.key}.example.com/oauth/authorize"
    )
    state = secrets.token_urlsafe(16)
    config = dict(connection.config or {})
    config["oauth_state"] = state
    connection.config = config
    connection.save(update_fields=["config", "updated_at"])
    params = urlencode(
        {
            "client_id": schema.get("client_id", "hireflux-mock-client"),
            "redirect_uri": redirect_uri
            or f"https://app.hireflux.local/integrations/{provider.key}/callback",
            "response_type": "code",
            "state": state,
        }
    )
    return f"{base}?{params}"


def _mock_token_exchange(provider: IntegrationProvider, code: str) -> dict:
    """Mock OAuth2 token exchange (real providers plug in here)."""
    return {
        "access_token": f"mock_access_{secrets.token_hex(16)}",
        "refresh_token": f"mock_refresh_{secrets.token_hex(16)}",
        "expires_in": 3600,
    }


@transaction.atomic
def connect_connection(
    connection: IntegrationConnection,
    *,
    actor=None,
    redirect_uri: str = "",
    code: str = "",
) -> dict:
    """
    Establish a connection.

    OAuth2 providers return an authorization URL unless an authorization
    ``code`` is supplied (then a mock token exchange completes the flow).
    API-key and no-auth providers are connected immediately.
    """
    provider = connection.provider
    if provider.auth_type == IntegrationProvider.AuthType.OAUTH2:
        if code:
            tokens = _mock_token_exchange(provider, code)
            creds = dict(connection.credentials_encrypted or {})
            creds["access_token"] = encrypt_value(tokens["access_token"])
            creds["refresh_token"] = encrypt_value(tokens["refresh_token"])
            creds["expires_in"] = encrypt_value(tokens["expires_in"])
            connection.credentials_encrypted = creds
            connection.status = IntegrationConnection.Status.CONNECTED
            connection.last_error = ""
            connection.connected_by = actor
            connection.save(update_fields=[
                "credentials_encrypted", "status", "last_error",
                "connected_by", "updated_by", "updated_at",
            ])
            return {"connected": True, "provider": provider.key}
        return {"authorization_url": _build_oauth_authorization_url(connection, redirect_uri)}

    if provider.auth_type == IntegrationProvider.AuthType.API_KEY:
        creds = connection.credentials_encrypted or {}
        if creds.get("api_key"):
            raise ValidationError(
                "An api_key credential is required before connecting."
            )

    connection.status = IntegrationConnection.Status.CONNECTED
    connection.last_error = ""
    connection.connected_by = actor
    connection.save(update_fields=[
        "status", "last_error", "connected_by", "updated_by", "updated_at",
    ])
    return {"connected": True, "provider": provider.key}


@transaction.atomic
def disconnect_connection(connection: IntegrationConnection, *, actor=None) -> IntegrationConnection:
    """Disconnect a connection, preserving its configuration."""
    connection.status = IntegrationConnection.Status.DISCONNECTED
    connection.last_synced_at = None
    connection.last_error = ""
    connection.updated_by = actor
    connection.save(update_fields=[
        "status", "last_synced_at", "last_error", "updated_by", "updated_at",
    ])
    return connection


def test_connection(connection: IntegrationConnection) -> tuple[bool, str]:
    """
    Health-check a connection.

    Returns ``(ok, message)`` without persisting anything; callers decide
    how to record the outcome.
    """
    provider = connection.provider
    schema = provider.config_schema or {}
    base_url = schema.get("base_url") or f"https://{provider.key}.example.com"
    health_path = schema.get("health_path", "/health")

    if provider.auth_type == IntegrationProvider.AuthType.OAUTH2:
        creds = connection.credentials_encrypted or {}
        if not creds.get("access_token"):
            return False, "No access token stored for this connection."
        return True, "OAuth2 token present (mock health check)."

    if provider.auth_type == IntegrationProvider.AuthType.API_KEY:
        creds = connection.credentials_encrypted or {}
        api_key = creds.get("api_key")
        if not api_key:
            return False, "No api_key credential stored for this connection."
        status_code, body = _http_get(
            f"{base_url.rstrip('/')}/{health_path.lstrip('/')}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        if status_code is None:
            return False, body
        if 200 <= status_code < 300:
            return True, f"Provider responded HTTP {status_code}."
        return False, f"Provider responded HTTP {status_code}: {body[:300]}"

    # No auth required — treat as healthy if provider catalog is active.
    return True, "Provider requires no authentication (mock health check)."


@transaction.atomic
def sync_connection(connection: IntegrationConnection, *, actor=None) -> IntegrationConnection:
    """Run a health check and record a successful sync timestamp."""
    ok, message = test_connection(connection)
    connection.status = (
        IntegrationConnection.Status.CONNECTED
        if ok
        else IntegrationConnection.Status.ERROR
    )
    connection.last_error = "" if ok else message[:1000]
    if ok:
        connection.last_synced_at = timezone.now()
        config = dict(connection.config or {})
        config["last_sync_summary"] = f"Synced at {timezone.now().isoformat()}"
        connection.config = config
    connection.updated_by = actor
    connection.save(update_fields=[
        "status", "last_error", "last_synced_at", "config", "updated_by", "updated_at",
    ])
    return connection


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------


def _hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return f"hf_{secrets.token_urlsafe(32)}"


@transaction.atomic
def create_api_key(*, organization, name, scopes=None, is_active=True, expires_at=None, actor=None):
    """Create an API key. The plaintext key is returned exactly once."""
    plaintext = generate_api_key()
    key = ApiKey.objects.create(
        organization=organization,
        name=name,
        key_prefix=plaintext[:10],
        key_hash=_hash_api_key(plaintext),
        scopes=scopes or [],
        is_active=is_active,
        expires_at=expires_at,
        created_by=actor,
        updated_by=actor,
    )
    return key, plaintext


@transaction.atomic
def regenerate_api_key(key: ApiKey, *, actor=None) -> tuple[ApiKey, str]:
    """Replace the underlying key material; the old key stops working."""
    plaintext = generate_api_key()
    key.key_prefix = plaintext[:10]
    key.key_hash = _hash_api_key(plaintext)
    key.is_active = True
    key.updated_by = actor
    key.save(update_fields=["key_prefix", "key_hash", "is_active", "updated_by", "updated_at"])
    return key, plaintext


@transaction.atomic
def revoke_api_key(key: ApiKey, *, actor=None) -> ApiKey:
    """Revoke a key immediately."""
    key.is_active = False
    key.updated_by = actor
    key.save(update_fields=["is_active", "updated_by", "updated_at"])
    return key
