"""
Documents ViewSets: categories, templates, generated documents, e-sign, public sign.
"""
from django_filters import rest_framework as filters
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import (
    AuditMixin,
    OrgCreateMixin,
    OrgQuerysetMixin,
    SoftDeleteDestroyMixin,
)
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.documents import services
from apps.documents.models import (
    DocumentCategory,
    DocumentSignRequest,
    DocumentTemplate,
    GeneratedDocument,
)
from apps.documents.serializers import (
    CreateGeneratedDocumentSerializer,
    CreateSignRequestSerializer,
    DocumentCategorySerializer,
    DocumentSignRequestSerializer,
    DocumentTemplateSerializer,
    GeneratedDocumentSerializer,
    PublicSignDetailSerializer,
    PublicSignSubmitSerializer,
    RenderTemplateSerializer,
)

DOCUMENTS_PERMISSION_MAP = {
    "SAFE": ["documents.view"],
    "POST": ["documents.manage"],
    "PUT": ["documents.manage"],
    "PATCH": ["documents.manage"],
    "DELETE": ["documents.manage"],
}


def _resolve_related(organization, model, pk, label):
    """Resolve an optional related object scoped to the organization."""
    if not pk:
        return None
    obj = model.objects.for_org(organization).filter(pk=pk).first()
    if obj is None:
        raise serializers.ValidationError({label: f"{label} not found in this organization."})
    return obj


class DocumentCategoryViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = DOCUMENTS_PERMISSION_MAP
    search_fields = ["name", "description"]
    filterset_fields = ["is_active"]
    ordering = ["name"]
    audit_resource_type = "DocumentCategory"


class DocumentTemplateViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = DocumentTemplate.objects.select_related("category")
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = DOCUMENTS_PERMISSION_MAP
    search_fields = ["name", "description"]
    filterset_fields = ["category", "is_active"]
    ordering = ["name"]
    audit_resource_type = "DocumentTemplate"

    def get_permissions(self):
        action_perms = {
            "render": ["documents.view"],
            "duplicate": ["documents.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None):
        """Preview-render the template with the given variables (no persistence)."""
        template = self.get_object()
        ser = RenderTemplateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rendered = services.render_document(
            template, ser.validated_data.get("variables", {})
        )
        return Response(rendered)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        template = self.get_object()
        copy = services.duplicate_template(template, actor=request.user)
        return Response(
            DocumentTemplateSerializer(copy).data,
            status=status.HTTP_201_CREATED,
        )


class GeneratedDocumentFilter(filters.FilterSet):
    template = filters.UUIDFilter()
    related_candidate = filters.UUIDFilter()
    related_job = filters.UUIDFilter()
    related_offer = filters.UUIDFilter()
    status = filters.CharFilter()

    class Meta:
        model = GeneratedDocument
        fields = ["template", "related_candidate", "related_job", "related_offer", "status"]


class GeneratedDocumentViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = GeneratedDocument.objects.select_related(
        "template", "related_candidate", "related_job", "related_offer", "finalized_by"
    )
    serializer_class = GeneratedDocumentSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = DOCUMENTS_PERMISSION_MAP
    filterset_class = GeneratedDocumentFilter
    search_fields = ["title", "content_text"]
    ordering = ["-created_at"]
    audit_resource_type = "GeneratedDocument"

    def get_permissions(self):
        action_perms = {
            "finalize": ["documents.manage"],
            "void": ["documents.manage"],
            "download": ["documents.view"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = CreateGeneratedDocumentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        from apps.candidates.models import Candidate
        from apps.jobs.models import Job
        from apps.offers.models import Offer

        template = None
        if data.get("template_id"):
            template = (
                DocumentTemplate.objects.for_org(request.organization)
                .filter(pk=data["template_id"])
                .first()
            )
            if not template:
                return Response(
                    {"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND
                )

        document = services.create_generated_document(
            request.organization,
            template=template,
            title=data.get("title", ""),
            variables=data.get("variables", {}),
            related_candidate=_resolve_related(
                request.organization, Candidate, data.get("related_candidate_id"), "related_candidate"
            ),
            related_job=_resolve_related(
                request.organization, Job, data.get("related_job_id"), "related_job"
            ),
            related_offer=_resolve_related(
                request.organization, Offer, data.get("related_offer_id"), "related_offer"
            ),
            content_html=data.get("content_html", ""),
            content_text=data.get("content_text", ""),
            actor=request.user,
        )
        return Response(
            GeneratedDocumentSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        document = self.get_object()
        document = services.finalize_document(document, actor=request.user)
        return Response(GeneratedDocumentSerializer(document).data)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        document = self.get_object()
        document = services.void_document(document, actor=request.user)
        return Response(GeneratedDocumentSerializer(document).data)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Download the document body as a plain-text file."""
        document = self.get_object()
        content = document.content_text or document.content_html or ""
        filename = f"{(document.title or 'document').replace(' ', '_')}.txt"
        response = Response(content, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class DocumentSignRequestViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = DocumentSignRequest.objects.select_related("document").prefetch_related(
        "signatures"
    )
    serializer_class = DocumentSignRequestSerializer
    permission_classes = [IsOrgMember, HasPerm]
    permission_map = DOCUMENTS_PERMISSION_MAP
    filterset_fields = ["document", "signer_email", "status"]
    search_fields = ["signer_name", "signer_email"]
    ordering = ["-created_at"]
    audit_resource_type = "DocumentSignRequest"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        action_perms = {
            "send": ["documents.manage"],
            "resend": ["documents.manage"],
            "void": ["documents.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = CreateSignRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        document = (
            GeneratedDocument.objects.for_org(request.organization)
            .filter(pk=data["document_id"])
            .first()
        )
        if not document:
            return Response(
                {"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND
            )

        sign_request = services.create_sign_request(
            document,
            signer_name=data["signer_name"],
            signer_email=data["signer_email"],
            message=data.get("message", ""),
            actor=request.user,
        )
        return Response(
            DocumentSignRequestSerializer(sign_request).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        sign_request = self.get_object()
        sign_request = services.send_sign_request(sign_request, actor=request.user)
        return Response(DocumentSignRequestSerializer(sign_request).data)

    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        sign_request = self.get_object()
        sign_request = services.resend_sign_request(sign_request, actor=request.user)
        return Response(DocumentSignRequestSerializer(sign_request).data)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        sign_request = self.get_object()
        sign_request = services.void_sign_request(sign_request, actor=request.user)
        return Response(DocumentSignRequestSerializer(sign_request).data)


class PublicSignDetailView(APIView):
    """Public, unauthenticated view of a sign request by token."""

    permission_classes = []
    authentication_classes = []

    def get(self, request, token):
        sign_request = (
            DocumentSignRequest.objects.select_related("document")
            .filter(token=token, status=DocumentSignRequest.Status.PENDING)
            .first()
        )
        if not sign_request:
            return Response(
                {"detail": "Sign request not found."}, status=status.HTTP_404_NOT_FOUND
            )
        payload = PublicSignDetailSerializer(
            {
                "sign_request": sign_request,
                "document": sign_request.document,
                "signatures": sign_request.signatures.all(),
            }
        ).data
        return Response(payload)


class PublicSignSubmitView(APIView):
    """Public, unauthenticated signature submission by token."""

    permission_classes = []
    authentication_classes = []

    def post(self, request, token):
        sign_request = (
            DocumentSignRequest.objects.select_related("document")
            .filter(token=token)
            .first()
        )
        if not sign_request:
            return Response(
                {"detail": "Sign request not found."}, status=status.HTTP_404_NOT_FOUND
            )
        ser = PublicSignSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            sign_request = services.submit_signature(
                sign_request,
                name=ser.validated_data["name"],
                email=ser.validated_data["email"],
                signature_svg=ser.validated_data.get("signature_svg", ""),
                ip_address=getattr(request, "client_ip", None),
            )
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        payload = PublicSignDetailSerializer(
            {
                "sign_request": sign_request,
                "document": sign_request.document,
                "signatures": sign_request.signatures.all(),
            }
        ).data
        return Response(payload)
