"""
Reusable DRF viewset mixins for multi-tenant resources.
"""
from rest_framework.exceptions import PermissionDenied, ValidationError


class OrgQuerysetMixin:
    """Filter queryset to ``request.organization``."""

    org_field = "organization"

    def get_organization(self)
        org = getattr(self.request, "organization", None)
        if org is None and not getattr(self, "org_optional", False):
            raise PermissionDenied("Organization context required (X-Organization-Id).")
        return org

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is None:
            if getattr(self, "org_optional", False):
                return qs
            return qs.none()
        return qs


class OrgCreateMixin:
    """Inject organization (and optional created_by) on create."""

    def perform_create(self, serializer):
        org = getattr(self.request, "organization", None)
        if org is None:
            raise ValidationError({"organization": "Organization context required."})
        kwargs = {"organization": org}
        model = serializer.Meta.model
        if hasattr(model, "created_by"):
            kwargs["updated_by"] = self.request.user
        if hasattr(model, "updated_by"):
            kwargs["updated_by"] = self.request.user
        serializer.save(**kwargs)

    def perform_update(self, serializer):
        kwargs = {}
        model = serializer.Meta.model
        if hasattr(model, "updated_by"):
            kwargs["updated_by"] = self.request.user
        serializer.save(**kwargs)


class SoftDeleteDestroyMixin:
    """Use model soft-delete instead of hard DELETE."""

    def perform_destroy(self, instance):
        if hasattr(instance, "delete") and hasattr(instance, "is_deleted"):
            instance.delete()
        else:
            instance.delete()


class AuditMixin:
    """Log create/update/delete via core.audit.log_action."""

    audit_resource_type = None

    def _resource_type(self, instance=None):
        if self.audit_resource_type:
            return self.audit_resource_type
        if instance is not None:
            return instance.__class__.__name__
        return self.get_queryset().model.__name__

    def perform_create(self, serializer):
        super().perform_create(serializer)
        from apps.core.audit import log_action
        from apps.core.models import AuditLog

        instance = serializer.instance
        log_action(
            request=self.request,
            action=AuditLog.Action.CREATE,
            resource_type=self._resource_type(instance),
            resource_id=str(instance.pk),
            message=f"Created {self._resource_type(instance)}",
            metadata={"data": getattr(serializer, "validated_data", {})},
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        from apps.core.audit import log_action
        from apps.core.models import AuditLog

        instance = serializer.instance
        log_action(
            request=self.request,
            action=AuditLog.Action.UPDATE,
            resource_type=self._resource_type(instance),
            resource_id=str(instance.pk),
            message=f"Updated {self._resource_type(instance)}",
        )

    def perform_destroy(self, instance):
        from apps.core.audit import log_action
        from apps.core.models import AuditLog

        resource_type = self._resource_type(instance)
        resource_id = str(instance.pk)
        super().perform_destroy(instance)
        log_action(
            request=self.request,
            action=AuditLog.Action.DELETE,
            resource_type=resource_type,
            resource_id=resource_id,
            message=f"Deleted {resource_type}",
        )
