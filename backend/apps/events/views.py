"""
Event ViewSets: events, sessions, registrations, tasks, check-in.
"""
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.events.models import EventRegistration, EventSession, EventTask, RecruitingEvent
from apps.events.serializers import (
    CheckInManySerializer,
    EventRegistrationSerializer,
    EventSessionSerializer,
    EventTaskSerializer,
    RecruitingEventSerializer,
)
from apps.events import services


class RecruitingEventViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = RecruitingEvent.objects.select_related("organization")
    serializer_class = RecruitingEventSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["events.view"],
        "POST": ["events.manage"],
        "PUT": ["events.manage"],
        "PATCH": ["events.manage"],
        "DELETE": ["events.manage"],
    }
    filterset_fields = ["event_type", "status", "is_virtual"]
    search_fields = ["name", "description", "location"]
    ordering_fields = ["start_at", "end_at", "created_at", "name", "status"]
    ordering = ["-start_at"]
    audit_resource_type = "RecruitingEvent"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_permissions(self):
        action_perms = {
            "publish": ["events.manage"],
            "cancel": ["events.manage"],
            "complete": ["events.manage"],
            "sessions": ["events.view"],
            "registrations": ["events.view"],
            "export": ["events.view"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        event = self.get_object()
        event = services.publish_event(event, actor=request.user, request=request)
        return Response(RecruitingEventSerializer(event).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        event = self.get_object()
        event = services.cancel_event(event, actor=request.user, request=request)
        return Response(RecruitingEventSerializer(event).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        event = self.get_object()
        event = services.complete_event(event, actor=request.user, request=request)
        return Response(RecruitingEventSerializer(event).data)

    @action(detail=True, methods=["get", "post"], url_path="sessions")
    def sessions(self, request, pk=None):
        """Nested sessions under an event (list + create)."""
        event = self.get_object()
        if request.method == "GET":
            qs = EventSession.objects.filter(event=event, is_deleted=False).order_by("start_at")
            return Response(EventSessionSerializer(qs, many=True).data)
        ser = EventSessionSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        session = ser.save(
            organization=event.organization,
            event=event,
            created_by=request.user,
            updated_by=request.user,
        )
        return Response(EventSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="registrations")
    def registrations(self, request, pk=None):
        """List registrations for an event (paginated, filterable by status)."""
        event = self.get_object()
        qs = EventRegistration.objects.filter(event=event, is_deleted=False).select_related(
            "candidate"
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.order_by("-registered_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = EventRegistrationSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(EventRegistrationSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="export")
    def export(self, request, pk=None):
        """Download event registrations as CSV."""
        event = self.get_object()
        csv_text = services.export_registrations_csv(event)
        response = HttpResponse(csv_text, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="event-{event.pk}-registrations.csv"'
        return response


class EventSessionViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = EventSession.objects.select_related("event", "organization")
    serializer_class = EventSessionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["events.view"],
        "POST": ["events.manage"],
        "PUT": ["events.manage"],
        "PATCH": ["events.manage"],
        "DELETE": ["events.manage"],
    }
    filterset_fields = ["event"]
    search_fields = ["title", "speaker", "room", "description"]
    ordering_fields = ["start_at", "end_at", "created_at", "title"]
    ordering = ["start_at", "created_at"]
    audit_resource_type = "EventSession"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs


class EventRegistrationViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = EventRegistration.objects.select_related("event", "candidate", "organization")
    serializer_class = EventRegistrationSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["events.view"],
        "POST": ["events.manage"],
        "PUT": ["events.manage"],
        "PATCH": ["events.manage"],
        "DELETE": ["events.manage"],
    }
    filterset_fields = ["event", "candidate", "status"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["registered_at", "checked_in_at", "created_at", "email"]
    ordering = ["-registered_at"]
    audit_resource_type = "EventRegistration"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_permissions(self):
        action_perms = {
            "check_in": ["events.manage"],
            "check_in_many": ["events.manage"],
            "cancel": ["events.manage"],
            "waitlist": ["events.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        reg = self.get_object()
        reg = services.check_in_registration(reg, actor=request.user, request=request)
        return Response(EventRegistrationSerializer(reg).data)

    @action(detail=False, methods=["post"], url_path="check-in-many")
    def check_in_many(self, request):
        ser = CheckInManySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = services.check_in_many(
            request.organization,
            ser.validated_data["registration_ids"],
            actor=request.user,
            request=request,
        )
        return Response(result)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        reg = self.get_object()
        reg = services.cancel_registration(reg, actor=request.user, request=request)
        return Response(EventRegistrationSerializer(reg).data)

    @action(detail=True, methods=["post"])
    def waitlist(self, request, pk=None):
        reg = self.get_object()
        reg = services.waitlist_registration(reg, actor=request.user, request=request)
        return Response(EventRegistrationSerializer(reg).data)


class EventTaskViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = EventTask.objects.select_related("event", "assignee", "organization")
    serializer_class = EventTaskSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["events.view"],
        "POST": ["events.manage"],
        "PUT": ["events.manage"],
        "PATCH": ["events.manage"],
        "DELETE": ["events.manage"],
    }
    filterset_fields = ["event", "assignee", "status"]
    search_fields = ["title", "notes"]
    ordering_fields = ["due_at", "created_at", "title", "status"]
    ordering = ["due_at", "created_at"]
    audit_resource_type = "EventTask"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_permissions(self):
        action_perms = {
            "complete": ["events.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task = services.complete_event_task(task, actor=request.user, request=request)
        return Response(EventTaskSerializer(task).data)
