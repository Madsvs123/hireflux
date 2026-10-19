"""
Calendar ViewSets: accounts, availability, slots, links, bookings, public pages.
"""
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.calendar.models import (
    AvailabilityRule,
    BookingRequest,
    CalendarAccount,
    InterviewSlot,
    SchedulingLink,
)
from apps.calendar.serializers import (
    AvailabilityRuleSerializer,
    BookingRequestSerializer,
    BulkGenerateSlotsSerializer,
    CalendarAccountSerializer,
    HoldSlotSerializer,
    InterviewSlotSerializer,
    PublicBookingSerializer,
    SchedulingLinkSerializer,
)
from apps.calendar import services
from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser


class CalendarAccountViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = CalendarAccount.objects.select_related("user", "organization")
    serializer_class = CalendarAccountSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["calendar.view"],
        "POST": ["calendar.manage"],
        "PUT": ["calendar.manage"],
        "PATCH": ["calendar.manage"],
        "DELETE": ["calendar.manage"],
    }
    filterset_fields = ["user", "provider", "is_primary", "sync_enabled"]
    search_fields = ["email", "calendar_id"]
    ordering_fields = ["created_at", "email", "provider", "last_synced_at"]
    ordering = ["-is_primary", "-created_at"]
    audit_resource_type = "CalendarAccount"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_permissions(self):
        action_perms = {
            "connect": ["calendar.manage"],
            "sync": ["calendar.manage"],
            "disconnect": ["calendar.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def connect(self, request, pk=None):
        account = self.get_object()
        result = services.connect_account(account, actor=request.user, request=request)
        return Response(result)

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        account = self.get_object()
        from apps.calendar.tasks import sync_calendar_events

        sync_calendar_events.delay(str(account.pk))
        return Response(
            {"queued": True, "account_id": str(account.pk)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def disconnect(self, request, pk=None):
        account = self.get_object()
        account = services.disconnect_account(account, actor=request.user, request=request)
        return Response(CalendarAccountSerializer(account).data)


class AvailabilityRuleViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = AvailabilityRule.objects.select_related("user", "organization")
    serializer_class = AvailabilityRuleSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["calendar.view"],
        "POST": ["calendar.manage"],
        "PUT": ["calendar.manage"],
        "PATCH": ["calendar.manage"],
        "DELETE": ["calendar.manage"],
    }
    filterset_fields = ["user", "is_active"]
    search_fields = ["title"]
    ordering_fields = ["title", "start_time", "end_time", "created_at"]
    ordering = ["title", "start_time"]
    audit_resource_type = "AvailabilityRule"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs


class InterviewSlotViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """Slots are generated from availability rules; list + lifecycle actions only."""

    queryset = InterviewSlot.objects.select_related("user", "availability_rule", "booking_request")
    serializer_class = InterviewSlotSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["calendar.view"]}
    filterset_fields = ["user", "availability_rule", "status", "booking_request"]
    search_fields = []
    ordering_fields = ["start_at", "end_at", "created_at", "status"]
    ordering = ["start_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        start = self.request.query_params.get("start_date")
        end = self.request.query_params.get("end_date")
        if start:
            qs = qs.filter(start_at__gte=start)
        if end:
            qs = qs.filter(start_at__lte=end)
        return qs

    def get_permissions(self):
        action_perms = {
            "bulk_generate": ["calendar.view"],
            "hold": ["calendar.manage"],
            "release": ["calendar.manage"],
            "cancel": ["calendar.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=False, methods=["post"], url_path="bulk-generate")
    def bulk_generate(self, request):
        ser = BulkGenerateSlotsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.filter(pk=data["user"]).first()
        if user is None:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        result = services.generate_slots(
            organization=request.organization,
            user=user,
            start_date=data["start_date"],
            end_date=data["end_date"],
            duration_minutes=data["duration_minutes"],
            rule_ids=data.get("rule_ids") or None,
            actor=request.user,
            request=request,
        )
        return Response(result)

    @action(detail=True, methods=["post"])
    def hold(self, request, pk=None):
        slot = self.get_object()
        ser = HoldSlotSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        slot = services.hold_slot(
            slot,
            hold_minutes=ser.validated_data["hold_minutes"],
            actor=request.user,
            request=request,
        )
        return Response(InterviewSlotSerializer(slot).data)

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        slot = self.get_object()
        slot = services.release_slot(slot, actor=request.user, request=request)
        return Response(InterviewSlotSerializer(slot).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        slot = self.get_object()
        slot = services.cancel_slot(slot, actor=request.user, request=request)
        return Response(InterviewSlotSerializer(slot).data)


class SchedulingLinkViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = SchedulingLink.objects.select_related("owner", "job", "organization")
    serializer_class = SchedulingLinkSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["calendar.view"],
        "POST": ["calendar.manage"],
        "PUT": ["calendar.manage"],
        "PATCH": ["calendar.manage"],
        "DELETE": ["calendar.manage"],
    }
    filterset_fields = ["owner", "job", "is_active"]
    search_fields = ["name", "slug"]
    ordering_fields = ["created_at", "name", "duration_minutes", "is_active"]
    ordering = ["-created_at"]
    audit_resource_type = "SchedulingLink"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_permissions(self):
        action_perms = {
            "duplicate": ["calendar.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        link = self.get_object()
        copy = services.duplicate_link(link, actor=request.user, request=request)
        return Response(SchedulingLinkSerializer(copy).data, status=status.HTTP_201_CREATED)


class BookingRequestViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = BookingRequest.objects.select_related(
        "scheduling_link", "scheduling_link__owner", "candidate", "organization"
    )
    serializer_class = BookingRequestSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["calendar.view"],
        "POST": ["calendar.manage"],
        "PUT": ["calendar.manage"],
        "PATCH": ["calendar.manage"],
        "DELETE": ["calendar.manage"],
    }
    filterset_fields = ["scheduling_link", "candidate", "status", "email"]
    search_fields = ["name", "email", "notes"]
    ordering_fields = ["created_at", "requested_slot_start", "confirmed_at", "status"]
    ordering = ["-created_at"]
    audit_resource_type = "BookingRequest"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_permissions(self):
        action_perms = {
            "confirm": ["calendar.manage"],
            "cancel": ["calendar.manage"],
            "decline": ["calendar.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        booking = services.confirm_booking(booking, actor=request.user, request=request)
        return Response(BookingRequestSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        booking = services.cancel_booking(booking, actor=request.user, request=request)
        return Response(BookingRequestSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        booking = self.get_object()
        booking = services.decline_booking(booking, actor=request.user, request=request)
        return Response(BookingRequestSerializer(booking).data)


def _owner_display(owner) -> str:
    if owner is None:
        return ""
    name = f"{owner.first_name} {owner.last_name}".strip()
    return name or owner.email


class PublicSchedulingSlotsView(APIView):
    """Anonymous: available slots for a public scheduling link."""

    permission_classes = []
    authentication_classes = []

    def get(self, request, slug=None):
        link = (
            SchedulingLink.all_objects.filter(slug=slug, is_active=True, is_deleted=False)
            .select_related("organization", "owner", "job")
            .first()
        )
        if link is None:
            return Response(
                {"detail": "Scheduling link not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )
        slots = services.public_available_slots(link)
        return Response(
            {
                "slug": link.slug,
                "name": link.name,
                "owner": {"id": str(link.owner_id), "name": _owner_display(link.owner)},
                "job_title": link.job.title if link.job else None,
                "duration_minutes": link.duration_minutes,
                "timezone": link.timezone,
                "slots": [
                    {"start_at": slot["start_at"], "end_at": slot["end_at"]} for slot in slots
                ],
            }
        )


class PublicSchedulingBookView(APIView):
    """Anonymous: create a booking through a public scheduling link."""

    permission_classes = []
    authentication_classes = []

    def post(self, request, slug=None):
        link = (
            SchedulingLink.all_objects.filter(slug=slug, is_active=True, is_deleted=False)
            .select_related("organization")
            .first()
        )
        if link is None:
            return Response(
                {"detail": "Scheduling link not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = PublicBookingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            booking = services.create_public_booking(link, ser.validated_data)
        except Exception as exc:  # noqa: BLE001 — surfaced as 400 for public safety
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {
                "status": booking.status,
                "confirmation_token": booking.confirmation_token,
                "requested_slot_start": booking.requested_slot_start,
                "expires_at": timezone.now(),
            },
            status=status.HTTP_201_CREATED,
        )
