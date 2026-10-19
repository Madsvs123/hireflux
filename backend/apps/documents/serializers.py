"""
Serializers for documents domain.
"""
from rest_framework import serializers

from apps.documents.models import (
    DocumentCategory,
    DocumentSignature,
    DocumentSignRequest,
    DocumentTemplate,
    GeneratedDocument,
)


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class DocumentTemplateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = DocumentTemplate
        fields = [
            "id",
            "category",
            "category_name",
            "name",
            "description",
            "body_html",
            "body_text",
            "variables",
            "default_currency",
            "is_active",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "category_name",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    related_candidate_name = serializers.CharField(
        source="related_candidate.full_name", read_only=True
    )
    related_job_title = serializers.CharField(source="related_job.title", read_only=True)
    related_offer_title = serializers.CharField(source="related_offer.title", read_only=True)
    finalized_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedDocument
        fields = [
            "id",
            "template",
            "template_name",
            "title",
            "content_html",
            "content_text",
            "status",
            "related_candidate",
            "related_candidate_name",
            "related_job",
            "related_job_title",
            "related_offer",
            "related_offer_title",
            "finalized_at",
            "finalized_by",
            "finalized_by_name",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "template_name",
            "related_candidate_name",
            "related_job_title",
            "related_offer_title",
            "status",
            "finalized_at",
            "finalized_by",
            "finalized_by_name",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_finalized_by_name(self, obj):
        if obj.finalized_by_id is None:
            return None
        name = f"{obj.finalized_by.first_name} {obj.finalized_by.last_name}".strip()
        return name or obj.finalized_by.email


class DocumentSignRequestSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source="document.title", read_only=True)
    signature_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentSignRequest
        fields = [
            "id",
            "token",
            "document",
            "document_title",
            "signer_name",
            "signer_email",
            "status",
            "message",
            "signed_at",
            "sent_at",
            "expires_at",
            "signature_data",
            "signature_count",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "token",
            "document_title",
            "status",
            "signed_at",
            "sent_at",
            "signature_data",
            "signature_count",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_signature_count(self, obj):
        return obj.signatures.count()


class DocumentSignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentSignature
        fields = [
            "id",
            "sign_request",
            "name",
            "email",
            "signature_svg",
            "ip_address",
            "signed_at",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class PublicSignDetailSerializer(serializers.Serializer):
    sign_request = DocumentSignRequestSerializer(read_only=True)
    document = GeneratedDocumentSerializer(read_only=True)
    signatures = DocumentSignatureSerializer(many=True, read_only=True)


class CreateGeneratedDocumentSerializer(serializers.Serializer):
    template_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    variables = serializers.DictField(required=False, default=dict)
    related_candidate_id = serializers.UUIDField(required=False, allow_null=True)
    related_job_id = serializers.UUIDField(required=False, allow_null=True)
    related_offer_id = serializers.UUIDField(required=False, allow_null=True)
    content_html = serializers.CharField(required=False, allow_blank=True, default="")
    content_text = serializers.CharField(required=False, allow_blank=True, default="")


class RenderTemplateSerializer(serializers.Serializer):
    variables = serializers.DictField(required=False, default=dict)


class CreateSignRequestSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    signer_name = serializers.CharField()
    signer_email = serializers.CharField()
    message = serializers.CharField(required=False, allow_blank=True, default="")


class PublicSignSubmitSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    signature_svg = serializers.CharField(required=False, allow_blank=True, default="")
