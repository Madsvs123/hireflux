"""
Audit logging helpers.
"""
import logging

from apps.core.models import AuditLog

logger = logging.getLogger(__name__)


def log_action(
    *,
    request=None,
    actor=None,
    organization=None,
    action,
    resource_type="",
    resource_id="",
    message="",
    metadata=None,
    ip_address=None,
    user_agent="",
    request_id="",
):
    """
    Persist an AuditLog entry. Safe to call from views, services, and signals.
    """
    if request is not None
        actor = actor or getattr(request, "user", None)
        if actor is not None and not getattr(actor, "is_authenticated", False):
            actor = None
        organization = organization or getattr(request, "organization", None)
        ip_address = ip_address or getattr(request, "client_ip", None)
        user_agent = user_agent or getattr(request, "client_user_agent", "")
        request_id = request_id or getattr(request, "request_id", "")

    # Sanitize metadata — drop non-JSON-serializable values best-effort
    clean_meta = {}
    if metadata:
        for key, value in metadata.items():
            try:
                if hasattr(value, "pk"):
                    clean_meta[key] = str(value.pk)
                elif isinstance(value, (str, int, float, bool, type(None), list)):
                    clean_meta[key] = value
                else:
                    clean_meta[key] = str(value)
            except Exception:  # noqa: BLE001
                clean_meta[key] = repr(value)

    try:
        return AuditLog.objects.create(
            organization=organization,
            actor=actor if actor and getattr(actor, "is_authenticated", True) else None,
            action=action,
            resource_type=resource_type or "",
            resource_id=str(resource_id) if resource_id else "",
            message=message or "",
            metadata=clean_meta,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:512],
            request_id=request_id or "",
        )
    except Exception:
        return None
