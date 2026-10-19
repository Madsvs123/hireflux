"""
Candidate portal views — applications, interviews, assessments, docs, offers, messages.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assessments.models import AssessmentAssignment
from apps.assessments.serializers import AssessmentQuestionPublicSerializer
from apps.candidates.models import Candidate, CandidateDocument
from apps.comms.models import MessageThread
from apps.core.permissions import IsCandidateUser
from apps.interviews.models import Interview
from apps.offers.models import Offer
from apps.pipelines.models import Application
from apps.portal.serializers import (
    PortalApplicationSerializer,
    PortalApplicationStatusSerializer,
    PortalAssessmentSerializer,
    PortalAssessmentSubmitSerializer,
    PortalDocumentSerializer,
    PortalDocumentUploadSerializer,
    PortalInterviewSerializer,
    PortalMessageSerializer,
    PortalMessageThreadSerializer,
    PortalOfferRespondSerializer,
    PortalOfferSerializer,
    PortalSendMessageSerializer,
)


class OwnsCandidateMixin:
    """Resolve Candidate profiles owned by the authenticated candidate user."""

    def get_candidate_ids(self):
        return list(
            Candidate.objects.filter(user=self.request.user, is_deleted=False).values_list(
                "pk", flat=True
            )
        )

    def get_candidates(self):
        return Candidate.objects.filter(user=self.request.user, is_deleted=False)

    def scoped_org(self):
        return getattr(self.request, "organization", None)

    def filter_by_org(self, qs, field="organization"):
        org = self.scoped_org()
        if org is not None:
            return qs.filter(**{field: org})
        return qs


class PortalApplicationViewSet(OwnsCandidateMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PortalApplicationSerializer
    permission_classes = [IsAuthenticated, IsCandidateUser]
    allow_candidates = True
    org_optional = True

    def get_queryset(self):
        ids = self.get_candidate_ids()
        qs = Application.objects.filter(candidate_id__in=ids).select_related(
            "job", "stage", "organization"
        )
        return self.filter_by_org(qs).order_by("applied_at")

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        application = self.get_object()
        stage = application.stage
        payload = {
            "application_id": application.pk,
            "status": application.status,
            "stage_name": stage.name if stage else None,
            "stage_type": stage.stage_type if stage else None,
            "applied_at": application.applied_at,
            "stage_entered_at": application.stage_entered_at,
            "message": _status_message(application),
        }
        return Response(PortalApplicationStatusSerializer(payload).data)


def _status_message(application: Application) -> str:
    if application.status == Application.Status.HIRED:
        return "Congratulations — you have been hired."
    if application.status == Application.Status.REJECTED:
        return "This application is no longer under consideration."
    if application.status == Application.Status.WITHDRAWN:
        return "You withdrew this application."
    stage = application.stage
    if stage:
        return f"Your application is currently in: {stage.name}."
    return "Your application is being reviewed."


class PortalInterviewViewSet(OwnsCandidateMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PortalInterviewSerializer
    permission_classes = [IsAuthenticated, IsCandidateUser]
    allow_candidates = True
    org_optional = True

    def get_queryset(self):
        ids = self.get_candidate_ids()
        qs = Interview.objects.filter(candidate_id__in=ids).filter(
            status=Interview.Status.CANCELLED
        ).select_related("job", "application")
        return self.filter_by_org(qs).order_by("scheduled_start")


class PortalAssessmentViewSet(OwnsCandidateMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PortalAssessmentSerializer
    permission_classes = [IsAuthenticated, IsCandidateUser]
    allow_candidates = True
    org_optional = True

    def get_queryset(self):
        ids = self.get_candidate_ids()
        qs = AssessmentAssignment.objects.filter(candidate_id__in=ids).select_related(
            "template", "job", "application"
        )
        return self.filter_by_org(qs).order_by("-created_at")

    @action(detail=True, methods=["get"])
    def questions(self, request, pk=None):
        assignment = self.get_object()
        if assignment.status in (
            AssessmentAssignment.Status.CANCELLED,
            AssessmentAssignment.Status.EXPIRED,
        ):
            return Response({"detail": "Assessment is not available."}, status=400)
        qs = assignment.template.questions.all()
        return Response(AssessmentQuestionPublicSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="submit-answers")
    def submit_answers(self, request, pk=None):
        assignment = self.get_object()
        ser = PortalAssessmentSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.assessments import services as assessment_services

        try:
            assignment = assessment_services.submit_answers(
                assignment,
                ser.validated_data["answers"],
                actor=request.user,
                auto_score=True,
                request=request,
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PortalAssessmentSerializer(assignment).data)


class PortalDocumentViewSet(OwnsCandidateMixin, viewsets.ModelViewSet):
    serializer_class = PortalDocumentSerializer
    permission_classes = [IsAuthenticated, IsCandidateUser]
    allow_candidates = True
    org_optional = True
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        ids = self.get_candidate_ids()
        qs = CandidateDocument.objects.filter(candidate_id__in=ids)
        return self.filter_by_org(qs).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        ser = PortalDocumentUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        candidates = self.get_candidates()
        org = self.scoped_org()
        if org:
            candidates = candidates.filter(organization=org)
        candidate = None
        if data.get("candidate_id"):
            candidate = candidates.filter(pk=data["candidate_id"]).first()
        else:
            candidate = candidates.first()
        if not candidate:
            return Response(
                {"detail": "No candidate profile linked to this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload = data["file"]
        doc = CandidateDocument.objects.create(
            organization=candidate.organization,
            candidate=candidate,
            doc_type=data.get("doc_type", CandidateDocument.DocType.RESUME),
            title=data.get("title") or getattr(upload, "name", ""),
            file=upload,
            file_name=getattr(upload, "name", ""),
            content_type=getattr(upload, "content_type", "") or "",
            file_size=getattr(upload, "size", None),
            is_primary=data.get("is_primary", False),
            created_by=request.user,
            updated_by=request.user,
        )
        if doc.is_primary:
            CandidateDocument.objects.filter(candidate=candidate).exclude(pk=doc.pk).update(
                is_primary=False
            )
        return Response(PortalDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class PortalOfferViewSet(OwnsCandidateMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PortalOfferSerializer
    permission_classes = [IsAuthenticated, IsCandidateUser]
    allow_candidates = True
    org_optional = True

    def get_queryset(self):
        ids = self.get_candidate_ids()
        qs = Offer.objects.filter(
            candidate_id__in=ids,
            status__in=[
                Offer.Status.SENT,
                Offer.Status.ACCEPTED,
                Offer.Status.DECLINED,
                Offer.Status.EXPIRED,
            ],
        ).select_related("job", "organization", "application")
        return self.filter_by_org(qs).order_by("-sent_at", "-created_at")

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        offer = self.get_object()
        ser = PortalOfferRespondSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.offers import services as offer_services

        try:
            if ser.validated_data["action"] == "accept":
                offer = offer_services.accept_offer(
                    offer,
                    note=ser.validated_data.get("note", ""),
                    actor=request.user,
                    request=request,
                )
            else:
                offer = offer_services.reject_offer(
                    offer,
                    note=ser.validated_data.get("note", ""),
                    actor=request.user,
                    request=request,
                )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PortalOfferSerializer(offer).data)


class PortalMessageViewSet(OwnsCandidateMixin, viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsCandidateUser]
    allow_candidates = True
    org_optional = True

    def list(self, request):
        threads = MessageThread.objects.filter(participants__user=request.user)
        org = self.scoped_org()
        if org:
            threads = threads.filter(organization=org)
        threads = threads.distinct().order_by("-last_message_at", "-created_at")
        return Response(PortalMessageThreadSerializer(threads, many=True).data)

    def retrieve(self, request, pk=None):
        thread = (
            MessageThread.objects.filter(pk=pk, participants__user=request.user)
            .distinct()
            .first()
        )
        if not thread:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        from apps.comms import services as comms_services

        comms_services.mark_thread_read(thread, request.user)
        messages = thread.messages.select_related("sender").order_by("created_at")
        return Response(
            {
                "thread": PortalMessageThreadSerializer(thread).data,
                "messages": PortalMessageSerializer(messages, many=True).data,
            }
        )

    def create(self, request):
        ser = PortalSendMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        from apps.comms import services as comms_services

        candidate = self.get_candidates().first()
        org = self.scoped_org() or (candidate.organization if candidate else None)
        if org is None:
            return Response(
                {"detail": "Organization context required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        thread = None
        if data.get("thread_id"):
            thread = (
                MessageThread.objects.filter(
                    pk=data["thread_id"], participants__user=request.user, organization=org
                )
                .distinct()
                .first()
            )
            if not thread:
                return Response({"detail": "Thread not found."}, status=status.HTTP_404_NOT_FOUND)

        application = None
        if data.get("application_id"):
            application = (
                Application.objects.filter(
                    pk=data["application_id"],
                    candidate_id__in=self.get_candidate_ids(),
                    organization=org,
                )
                .select_related("job", "candidate")
                .first()
            )

        thread, message = comms_services.send_message(
            organization=org,
            sender=request.user,
            body=data["body"],
            thread=thread,
            subject=data.get("subject", "") or "Candidate message",
            candidate=candidate,
            application=application,
            thread_type=MessageThread.ThreadType.CANDIDATE,
        )
        return Response(
            {
                "thread": PortalMessageThreadSerializer(thread).data,
                "message": PortalMessageSerializer(message).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PortalMeView(OwnsCandidateMixin, APIView):
    permission_classes = [IsAuthenticated, IsCandidateUser]
    allow_candidates = True
    org_optional = True

    def get(self, request):
        candidates = self.get_candidates()
        org = self.scoped_org()
        if org:
            candidates = candidates.filter(organization=org)
        return Response(
            {
                "user": {
                    "id": str(request.user.pk),
                    "email": request.user.email,
                    "first_name": request.user.first_name,
                    "last_name": request.user.last_name,
                },
                "candidates": [
                    {
                        "id": str(c.pk),
                        "organization_id": str(c.organization_id),
                        "full_name": c.full_name,
                        "email": c.email,
                    }
                    for c in candidates
                ],
            }
        )
