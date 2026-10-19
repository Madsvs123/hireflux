"""
Comms ViewSets: notifications (mark read) and messaging.
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.comms import services
from apps.comms.models import Message, MessageThread
from apps.comms.serializers import (
    MessageSerializer,
    MessageThreadSerializer,
    NotificationSerializer,
    SendMessageSerializer,
)
from apps.core.mixins import OrgQuerysetMixin
from apps.core.models import Notification
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """User's in-app notifications (core.Notification)."""

    serializer_class = NotificationSerializer
    permission_classes = [IsOrgMember]
    org_optional = True
    allow_candidates = True
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(Q(organization=org) | Q(organization__isnull=True))
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() in ("1", "true", "yes"))
        return qs

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        qs = self.get_queryset().filter(is_read=False)
        updated = qs.update(is_read=True, read_at=timezone.now())
        return Response({"marked": updated})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread": count})


class MessageThreadViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    queryset = MessageThread.objects.prefetch_related("participants__user", "messages")
    serializer_class = MessageThreadSerializer
    permission_classes = [IsOrgMember, HasPerm]
    permission_map = {
        "SAFE": ["comms.view"],
        "POST": ["comms.send"],
        "PUT": ["comms.send"],
        "PATCH": ["comms.send"],
        "DELETE": ["comms.send"],
    }
    filterset_fields = ["thread_type", "candidate", "application", "job", "is_closed"]
    search_fields = ["subject"]
    ordering = ["-last_message_at", "-created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # Staff see org threads they participate in or all if staff with view
        if getattr(user, "user_type", None) == "candidate":
            return qs.filter(participants__user=user)
        # Staff: threads in org (optionally filter to participating)
        mine = self.request.query_params.get("mine")
        if mine and mine.lower() in ("1", "true", "yes"):
            qs = qs.filter(participants__user=user)
        return qs.distinct()

    def create(self, request, *args, **kwargs):
        ser = SendMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._send(request, ser.validated_data)

    def _send(self, request, data):
        from apps.candidates.models import Candidate
        from apps.pipelines.models import Application
        from apps.jobs.models import Job

        org = request.organization
        thread = None
        if data.get("thread_id"):
            thread = MessageThread.objects.for_org(org).filter(pk=data["thread_id"]).first()
            if not thread:
                return Response({"detail": "Thread not found."}, status=status.HTTP_404_NOT_FOUND)

        candidate = None
        application = None
        job = None
        if data.get("candidate_id"):
            candidate = Candidate.objects.for_org(org).filter(pk=data["candidate_id"]).first()
        if data.get("application_id"):
            application = (
                Application.objects.for_org(org)
                .select_related("job", "candidate")
                .filter(pk=data["application_id"])
                .first()
            )
            if application:
                candidate = candidate or application.candidate
                job = application.job
        if data.get("job_id"):
            job = Job.objects.for_org(org).filter(pk=data["job_id"]).first() or job

        thread, message = services.send_message(
            organization=org,
            sender=request.user,
            body=data["body"],
            thread=thread,
            subject=data.get("subject", ""),
            participant_ids=data.get("participant_ids") or [],
            candidate=candidate,
            application=application,
            job=job,
            thread_type=data.get("thread_type", MessageThread.ThreadType.GENERAL),
            body_html=data.get("body_html", ""),
            attachments=data.get("attachments") or [],
        )
        return Response(
            {
                "thread": MessageThreadSerializer(thread, context={"request": request}).data,
                "message": MessageSerializer(message).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="send")
    def send(self, request):
        self.required_permissions = ["comms.send"]
        ser = SendMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._send(request, ser.validated_data)

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        thread = self.get_object()
        if request.method == "GET":
            qs = thread.messages.select_related("sender").order_by("-created_at")
            services.mark_thread_read(thread, request.user)
            return Response(MessageSerializer(qs, many=True).data)

        body = request.data.get("body", "")
        if not body:
            return Response({"detail": "body is required."}, status=status.HTTP_400_BAD_REQUEST)
        thread, message = services.send_message(
            organization=request.organization,
            sender=request.user,
            body=body,
            thread=thread,
            body_html=request.data.get("body_html", ""),
            attachments=request.data.get("attachments") or [],
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        thread = self.get_object()
        participant = services.mark_thread_read(thread, request.user)
        if not participant:
            return Response(
                {"detail": "You are not a participant of this thread."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"last_read_at": participant.last_read_at})


class MessageViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Message.objects.select_related("thread", "sender")
    serializer_class = MessageSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["comms.view"]}
    filterset_fields = ["thread", "sender", "is_system"]
    ordering = ["-created_at"]
