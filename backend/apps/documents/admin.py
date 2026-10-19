"""
Django admin for documents domain.
"""
from django.contrib import admin

from apps.documents.models import (
    DocumentCategory,
    DocumentSignature,
    DocumentSignRequest,
    DocumentTemplate,
    GeneratedDocument,
)

AUDIT_READONLY = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    raw_id_fields = ("organization",)
    readonly_fields = AUDIT_READONLY


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "organization", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    raw_id_fields = ("organization", "category")
    readonly_fields = AUDIT_READONLY


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "template",
        "status",
        "related_candidate",
        "finalized_by",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("title", "content_text")
    raw_id_fields = (
        "organization",
        "template",
        "related_candidate",
        "related_job",
        "related_offer",
        "finalized_by",
    )
    readonly_fields = AUDIT_READONLY


@admin.register(DocumentSignRequest)
class DocumentSignRequestAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "signer_name",
        "signer_email",
        "status",
        "sent_at",
        "signed_at",
        "expires_at",
    )
    list_filter = ("status",)
    search_fields = ("signer_name", "signer_email")
    raw_id_fields = ("organization", "document")
    readonly_fields = AUDIT_READONLY + ("token", "signature_data")


@admin.register(DocumentSignature)
class DocumentSignatureAdmin(admin.ModelAdmin):
    list_display = ("sign_request", "name", "email", "ip_address", "signed_at")
    search_fields = ("name", "email")
    raw_id_fields = ("organization", "sign_request")
    readonly_fields = AUDIT_READONLY
