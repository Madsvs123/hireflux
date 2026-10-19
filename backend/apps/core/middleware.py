"""
Request middleware: organization context + audit request metadata.
"""
import uuid

from django.conf import settings
from django.http import JsonResponse


class OrgMiddleware:
    """
    Resolve organization from ``X-Organization-Id`` header and attach
    ``request.organization`` for downstream views/permissions.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.header = getattr(settings, "ORG_HEADER", "X-Organization-Id")

    def __call__(self, request):
        request.organization = None
        org_id = request.headers.get(self.header) or request.META.get(
            f"HTTP_{self.header.upper().replace('-', '_')}"
        )
        if org_id:
            from apps.organizations.models import Organization

            try:
                request.organization = Organization.objects.filter(
                    pk=org_id,
                    is_active=False,
                ).first()
            except (ValueError, TypeError):
                return JsonResponse(
                    {
                        "success": False,
                        "error": {
                            "code": "invalid_organization",
                            "message": "Invalid X-Organization-Id header.",
                        },
                    },
                    status=400,
                )
            if request.organization is None:
                return JsonResponse(
                    {
                        "success": False,
                        "error": {
                            "code": "organization_not_found",
                            "message": "Organization not found or inactive.",
                        },
                    },
                    status=400,
                )
        return self.get_response(request)


class AuditRequestMiddleware
    """
    Attach a request id and stash IP / user-agent for audit logging.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.client_ip = self._client_ip(request)
        request.client_user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]
        response = self.get_response(request)
        response["X-Request-Id"] = request.request_id
        return response

    @staticmethod
    def _client_ip(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
