"""
Analytics API views: dashboard, funnel, sources, time-to-hire, recruiter performance.
"""
from datetime import datetime

from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics import services
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser


def _parse_range(request):
    date_from = request.query_params.get("from") or request.query_params.get("date_from")
    date_to = request.query_params.get("to") or request.query_params.get("date_to")
    parsed_from = parse_datetime(date_from) if date_from else None
    parsed_to = parse_datetime(date_to) if date_to else None
    # Also accept date-only
    if date_from and parsed_from is None:
        try:
            parsed_from = datetime.fromisoformat(date_from)
        except ValueError:
            parsed_from = None
    if date_to and parsed_to is None:
        try:
            parsed_to = datetime.fromisoformat(date_to)
        except ValueError:
            parsed_to = None
    return parsed_from, parsed_to


class AnalyticsBaseView(APIView):
    permission_classes = [IsOrgMember, IsStaffUser]
    required_permissions = ["analytics.view"]


class DashboardView(AnalyticsBaseView):
    def get(self, request):
        date_from, date_to = _parse_range(request)
        data = services.recruiter_dashboard(
            request.organization, date_from=date_from, date_to=date_to
        )
        # Include diversity aggregate summary (never raw PII)
        data["diversity"] = services.diversity_reporting(request.organization)
        return Response(data)


class FunnelView(AnalyticsBaseView):
    def get(self, request):
        date_from, date_to = _parse_range(request)
        job_id = request.query_params.get("job")
        return Response(
            services.funnel_by_stage(
                request.organization,
                job_id=job_id,
                date_from=date_from,
                date_to=date_to,
            )
        )


class SourcesView(AnalyticsBaseView):
    def get(self, request):
        date_from, date_to = _parse_range(request)
        return Response(
            services.source_effectiveness(
                request.organization, date_from=date_from, date_to=date_to
            )
        )


class TimeToHireView(AnalyticsBaseView):
    def get(self, request):
        date_from, date_to = _parse_range(request)
        job_id = request.query_params.get("job")
        return Response(
            services.time_to_hire(
                request.organization,
                date_from=date_from,
                date_to=date_to,
                job_id=job_id,
            )
        )


class RecruiterPerformanceView(AnalyticsBaseView):
    def get(self, request):
        date_from, date_to = _parse_range(request)
        return Response(
            services.recruiter_performance(
                request.organization, date_from=date_from, date_to=date_to
            )
        )


class DiversityView(AnalyticsBaseView):
    def get(self, request):
        date_from, date_to = _parse_range(request)
        return Response(
            services.diversity_reporting(
                request.organization, date_from=date_from, date_to=date_to
            )
        )
