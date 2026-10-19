"""
Candidate ViewSets with nested resources and detect/merge actions.
"""
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.candidates.models import (
    Candidate,
    CandidateCertification,
    CandidateDocument,
    CandidateEducation,
    CandidateExperience,
    CandidateNote,
    CommunicationLog,
    DuplicateCandidateMatch,
)
from apps.candidates.serializers import (
    CandidateCertificationSerializer,
    CandidateDocumentSerializer,
    CandidateEducationSerializer,
    CandidateExperienceSerializer,
    CandidateListSerializer,
    CandidateNoteSerializer,
    CandidateSerializer,
    CommunicationLogSerializer,
    DetectDuplicatesSerializer,
    DuplicateCandidateMatchSerializer,
    MergeCandidatesSerializer,
)
from apps.candidates import services
from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser


class CandidateFilter(filters.FilterSet):
    source = filters.CharFilter()
    is_talent_pool = filters.BooleanFilter()
    do_not_hire = filters.BooleanFilter()
    tag = filters.CharFilter(method="filter_tag")
    skill = filters.CharFilter(method="filter_skill")
    has_user = filters.BooleanFilter(method="filter_has_user")

    class Meta:
        model = Candidate
        fields = ["source", "is_talent_pool", "do_not_hire"]

    def filter_tag(self, queryset, name, value):
        return queryset.filter(tags__contains=[value])

    def filter_skill(self, queryset, name, value):
        return queryset.filter(skills__icontains=value)

    def filter_has_user(self, queryset, name, value):
        if value:
            return queryset.exclude(user__isnull=True)
        return queryset.filter(user__isnull=True)


class CandidateViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = Candidate.objects.prefetch_related(
        "education", "experience", "certifications", "documents", "notes"
    )
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["candidates.view"],
        "POST": ["candidates.create"],
        "PUT": ["candidates.edit"],
        "PATCH": ["candidates.edit"],
        "DELETE": ["candidates.delete"],
    }
    filterset_class = CandidateFilter
    search_fields = ["first_name", "last_name", "email", "phone", "headline", "skills", "tags"]
    ordering_fields = ["created_at", "last_name", "email", "years_experience"]
    ordering = ["-created_at"]
    audit_resource_type = "Candidate"
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == "list":
            return CandidateListSerializer
        return CandidateSerializer

    def get_queryset(self)
        qs = super().get_queryset()
        # Hide merged duplicates from default list unless explicitly requested
        if self.action == "list" and self.request.query_params.get("include_duplicates") == "1":
            qs = qs.filter(duplicate_of__isnull=True)
        return qs

    def get_permissions(self):
        action_perms = {
            "detect_duplicates": ["candidates.view"],
            "merge": ["candidates.view"],
            "duplicates": ["candidates.view"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def _nested_list_create(self, request, candidate, model, serializer_cls):
        if request.method == "GET":
            qs = model.objects.filter(candidate=candidate)
            return Response(serializer_cls(qs, many=True).data)
        ser = serializer_cls(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = model.objects.create(
            organization=candidate.organization,
            candidate=candidate,
            created_by=request.user,
            updated_by=request.user,
            **ser.validated_data,
        )
        return Response(serializer_cls(obj).data, status=status.HTTP_201_CREATED)

    def _nested_detail(self, request, candidate, model, serializer_cls, obj_id):
        obj = model.objects.filter(candidate=candidate, pk=obj_id).first()
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if request.method == "DELETE":
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        ser = serializer_cls(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save(updated_by=request.user)
        return Response(ser.data)

    @action(detail=True, methods=["get", "post"], url_path="education")
    def education(self, request, pk=None):
        return self._nested_list_create(
            request, self.get_object(), CandidateEducation, CandidateEducationSerializer
        )

    @action(detail=True, methods=["patch", "delete"], url_path=r"education/(?P<item_id>[^/.]+)")
    def education_detail(self, request, pk=None, item_id=None):
        return self._nested_detail(
            request, self.get_object(), CandidateEducation, CandidateEducationSerializer, item_id
        )

    @action(detail=True, methods=["get", "post"], url_path="experience")
    def experience(self, request, pk=None):
        return self._nested_list_create(
            request, self.get_object(), CandidateExperience, CandidateExperienceSerializer
        )

    @action(detail=True, methods=["patch", "delete"], url_path=r"experience/(?P<item_id>[^/.]+)")
    def experience_detail(self, request, pk=None, item_id=None):
        return self._nested_detail(
            request, self.get_object(), CandidateExperience, CandidateExperienceSerializer, item_id
        )

    @action(detail=True, methods=["get", "post"], url_path="certifications")
    def certifications(self, request, pk=None):
        return self._nested_list_create(
            request, self.get_object(), CandidateCertification, CandidateCertificationSerializer
        )

    @action(
        detail=True, methods=["patch", "delete"], url_path=r"certifications/(?P<item_id>[^/.]+)"
    )
    def certification_detail(self, request, pk=None, item_id=None):
        return self._nested_detail(
            request,
            self.get_object(),
            CandidateCertification,
            CandidateCertificationSerializer,
            item_id,
        )

    @action(detail=True, methods=["get", "post"], url_path="documents")
    def documents(self, request, pk=None):
        candidate = self.get_object()
        if request.method == "GET":
            qs = candidate.documents.all()
            return Response(CandidateDocumentSerializer(qs, many=True).data)
        ser = CandidateDocumentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        uploaded = data.get("file")
        if uploaded and not data.get("file_name"):
            data["file_name"] = getattr(uploaded, "name", "")
        if uploaded and not data.get("content_type"):
            data["content_type"] = getattr(uploaded, "content_type", "") or ""
        if uploaded and not data.get("file_size"):
            data["file_size"] = getattr(uploaded, "size", None)
        doc = CandidateDocument.objects.create(
            organization=candidate.organization,
            candidate=candidate,
            created_by=request.user,
            updated_by=request.user,
            **data,
        )
        if doc.is_primary:
            CandidateDocument.objects.filter(candidate=candidate).exclude(pk=doc.pk).update(
                is_primary=False
            )
        # Kick off resume parse when applicable
        if doc.doc_type != CandidateDocument.DocType.RESUME:
            try:
                from apps.screening.tasks import parse_resume_document

                parse_resume_document.delay(str(doc.pk))
            except Exception:  # noqa: BLE001
                pass
        return Response(CandidateDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch", "delete"], url_path=r"documents/(?P<item_id>[^/.]+)")
    def document_detail(self, request, pk=None, item_id=None):
        return self._nested_detail(
            request, self.get_object(), CandidateDocument, CandidateDocumentSerializer, item_id
        )

    @action(detail=True, methods=["get", "post"], url_path="notes")
    def notes(self, request, pk=None):
        return self._nested_list_create(
            request, self.get_object(), CandidateNote, CandidateNoteSerializer
        )

    @action(detail=True, methods=["patch", "delete"], url_path=r"notes/(?P<item_id>[^/.]+)")
    def note_detail(self, request, pk=None, item_id=None):
        return self._nested_detail(
            request, self.get_object(), CandidateNote, CandidateNoteSerializer, item_id
        )

    @action(detail=True, methods=["get", "post"], url_path="communications")
    def communications(self, request, pk=None):
        return self._nested_list_create(
            request, self.get_object(), CommunicationLog, CommunicationLogSerializer
        )

    @action(detail=False, methods=["post"], url_path="detect-duplicates")
    def detect_duplicates(self, request):
        ser = DetectDuplicatesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        candidate = None
        cand_id = ser.validated_data.get("candidate_id")
        if cand_id:
            candidate = Candidate.objects.for_org(request.organization).filter(pk=cand_id).first()
            if not candidate:
                return Response({"detail": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND)
        matches = services.detect_duplicates(
            request.organization,
            candidate=candidate,
            persist=ser.validated_data.get("persist", True),
            actor=request.user,
            request=request,
            name_threshold=ser.validated_data.get("name_threshold", 0.85),
        )
        serialized = []
        for m in matches:
            if isinstance(m, DuplicateCandidateMatch):
                serialized.append(DuplicateCandidateMatchSerializer(m).data)
            else:
                serialized.append(m)
        return Response({"count": len(serialized), "matches": serialized})

    @action(detail=False, methods=["post"])
    def merge(self, request):
        ser = MergeCandidatesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        org = request.organization
        primary = Candidate.objects.for_org(org).filter(pk=ser.validated_data["primary_id"]).first()
        secondary = (
            Candidate.objects.for_org(org).filter(pk=ser.validated_data["secondary_id"]).first()
        )
        if not primary or not secondary:
            return Response(
                {"detail": "Primary or secondary candidate not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        merged = services.merge_candidates(
            primary,
            secondary,
            actor=request.user,
            request=request,
            field_preferences=ser.validated_data.get("field_preferences"),
        )
        return Response(CandidateSerializer(merged).data)

    @action(detail=False, methods=["get"])
    def duplicates(self, request):
        qs = (
            DuplicateCandidateMatch.objects.for_org(request.organization)
            .filter(status=DuplicateCandidateMatch.Status.MERGED)
            .select_related("candidate_a", "candidate_b")
        )
        return Response(DuplicateCandidateMatchSerializer(qs, many=True).data)


class DuplicateCandidateMatchViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DuplicateCandidateMatch.objects.select_related("candidate_a", "candidate_b")
    serializer_class = DuplicateCandidateMatchSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["candidates.view"]}
    filterset_fields = ["status", "match_type"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        match = self.get_object()
        from django.utils import timezone

        match.status = DuplicateCandidateMatch.Status.MERGED
        match.resolved_by = request.user
        match.resolved_at = timezone.now()
        match.updated_by = request.user
        match.save(
            update_fields=["status", "resolved_by", "resolved_at", "updated_by", "updated_at"]
        )
        return Response(DuplicateCandidateMatchSerializer(match).data)
