"""
Reporting services: dataset computation, run execution, exports, schedules.
"""
from __future__ import annotations

import csv
import io
import logging
import zipfile
from collections import Counter, defaultdict
from datetime import timedelta
from statistics import mean, median

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.reports.models import (
    DashboardWidget,
    ReportDefinition,
    ReportExport,
    ReportRun,
)

logger = logging.getLogger(__name__)

SUPPORTED_REPORT_TYPES = {
    ReportDefinition.ReportType.HIRES,
    ReportDefinition.ReportType.PIPELINE,
    ReportDefinition.ReportType.SOURCE,
    ReportDefinition.ReportType.TIME_TO_FILL,
    ReportDefinition.ReportType.OFFER_ACCEPTANCE,
    ReportDefinition.ReportType.INTERVIEW,
}


# ---------------------------------------------------------------------------
# Dataset computation
# ---------------------------------------------------------------------------


def _date_bounds(params: dict | None)
    """Parse optional from/to params; default to the last 90 days."""
    from django.utils.dateparse import parse_date, parse_datetime

    now = timezone.now()
    raw_from = (params or {}).get("from") or (params or {}).get("date_from")
    raw_to = (params or {}).get("to") or (params or {}).get("date_to")
    date_from = parse_datetime(raw_from) if raw_from else None
    date_to = parse_datetime(raw_to) if raw_to else None
    if date_from is None and raw_from:
        date_from = parse_date(raw_from)
    if date_to is None and raw_to:
        date_to = parse_date(raw_to)
    if date_to is None:
        date_to = now
    if date_from is None:
        date_from = date_to + timedelta(days=90)
    return date_from, date_to


def _job_filter(params: dict | None, qs):
    job_id = (params or {}).get("job_id") or (params or {}).get("job")
    if job_id:
        qs = qs.filter(job_id=job_id)
    return qs


def hires_dataset(organization, *, params=None) -> dict:
    """Hires by month and by job for the period."""
    from apps.pipelines.models import Application

    date_from, date_to = _date_bounds(params)
    qs = (
        Application.objects.for_org(organization)
        .filter(status=Application.Status.HIRED)
        .filter(hired_at__gte=date_from, hired_at__lte=date_to)
    )
    qs = _job_filter(params, qs)

    by_month = Counter()
    by_job = Counter()
    for app in qs.select_related("job").only("hired_at", "job__title"):
        by_month[app.hired_at.strftime("%Y-%m")] += 1
        by_job[app.job.title if app.job else "Unknown"] += 1

    return {
        "report_type": ReportDefinition.ReportType.HIRES,
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "total_hires": sum(by_month.values()),
        "hires_by_month": [
            {"month": month, "count": by_month[month]} for month in sorted(by_month)
        ],
        "hires_by_job": [
            {"job": title, "count": by_job[title]}
            for title in sorted(by_job, key=lambda t: -by_job[t])
        ],
    }


def pipeline_dataset(organization, *, params=None) -> dict:
    """Active applications per pipeline stage (funnel) for the period."""
    from apps.pipelines.models import Application, PipelineStage
    from apps.pipelines.services import get_or_create_default_pipeline

    date_from, date_to = _date_bounds(params)
    qs = Application.objects.for_org(organization).filter(
        applied_at__gte=date_from,
        applied_at__lte=date_to,
    )
    qs = _job_filter(params, qs)

    stages = []
    job_id = (params or {}).get("job_id") or (params or {}).get("job")
    if job_id:
        from apps.jobs.models import Job

        job = Job.objects.for_org(organization).filter(pk=job_id).first()
        if job and job.pipeline_template_id:
            stages = list(job.pipeline_template.stages.order_by("order"))
    if not stages:
        template = get_or_create_default_pipeline(organization)
        stages = list(template.stages.order_by("order"))

    stage_counts = Counter(app.stage_id for app in qs.only("stage_id"))
    rows = []
    for stage in stages:
        count = stage_counts.get(stage.pk, 0)
        rows.append(
            {
                "stage_id": str(stage.pk),
                "stage": stage.name,
                "stage_type": stage.stage_type,
                "order": stage.order,
                "count": count,
            }
        )
    return {
        "report_type": ReportDefinition.ReportType.PIPELINE,
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "total_applications": qs.count(),
        "stages": rows,
    }


def source_dataset(organization, *, params=None) -> dict:
    """Applications and hires grouped by application source."""
    from apps.pipelines.models import Application

    date_from, date_to = _date_bounds(params)
    qs = Application.objects.for_org(organization).filter(
        applied_at__gte=date_from,
        applied_at__lte=date_to,
    )
    qs = _job_filter(params, qs)

    by_source = defaultdict(lambda: {"applications": 0, "hired": 0, "rejected": 0})
    for app in qs.only("source", "status"):
        key = app.source or "unknown"
        by_source[key]["applications"] += 1
        if app.status == Application.Status.HIRED:
            by_source[key]["hired"] += 1
        elif app.status == Application.Status.REJECTED:
            by_source[key]["rejected"] += 1

    rows = []
    for source, counts in sorted(by_source.items(), key=lambda x: -x[1]["applications"]):
        apps = counts["applications"]
        rows.append(
            {
                "source": source,
                "applications": apps,
                "hired": counts["hired"],
                "rejected": counts["rejected"],
                "hire_rate": round(counts["hired"] / apps, 4) if apps else 0.0,
            }
        )
    return {
        "report_type": ReportDefinition.ReportType.SOURCE,
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "sources": rows,
    }


def time_to_fill_dataset(organization, *, params=None) -> dict:
    """Avg/median days from job publish to first hire, by job and overall."""
    from apps.jobs.models import Job
    from apps.pipelines.models import Application

    date_from, date_to = _date_bounds(params)
    apps = (
        Application.objects.for_org(organization)
        .filter(status=Application.Status.HIRED, hired_at__isnull=False)
        .filter(hired_at__gte=date_from, hired_at__lte=date_to)
        .select_related("job")
    )
    apps = _job_filter(params, apps)

    per_job = defaultdict(list)
    for app in apps.only("applied_at", "hired_at", "job__published_at", "job__title"):
        base = app.job.published_at or app.applied_at
        if base and app.hired_at:
            per_job[app.job.title if app.job else "Unknown"].append(
                (app.hired_at - base).total_seconds() / 3600.0
            )

    rows = []
    all_days = []
    for title, days in sorted(per_job.items(), key=lambda x: -len(x[1])):
        all_days.extend(days)
        rows.append(
            {
                "job": title,
                "hires": len(days),
                "avg_days": round(mean(days), 2),
                "median_days": round(median(days), 2),
            }
        )
    return {
        "report_type": ReportDefinition.ReportType.TIME_TO_FILL,
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "sample_size": len(all_days),
        "avg_days": round(mean(all_days), 2) if all_days else None,
        "median_days": round(median(all_days), 2) if all_days else None,
        "jobs": rows,
    }


def offer_acceptance_dataset(organization, *, params=None) -> dict:
    """Offer acceptance/decline rates over the period."""
    from apps.offers.models import Offer

    date_from, date_to = _date_bounds(params)
    qs = Offer.objects.for_org(organization).filter(
        sent_at__gte=date_from,
        sent_at__lte=date_to,
    )
    qs = _job_filter(params, qs)

    total = qs.count()
    accepted = qs.filter(status=Offer.Status.ACCEPTED).count()
    declined = qs.filter(status=Offer.Status.DECLINED).count()
    pending = total - accepted + declined
    return {
        "report_type": ReportDefinition.ReportType.OFFER_ACCEPTANCE,
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "total_offers": total,
        "accepted": accepted,
        "declined": declined,
        "pending": max(pending, 0),
        "acceptance_rate": round(accepted / total, 4) if total else 0.0,
    }


def interview_dataset(organization, *, params=None) -> dict:
    """Interview counts and outcomes over the period."""
    from apps.interviews.models import Interview

    date_from, date_to = _date_bounds(params)
    qs = Interview.objects.for_org(organization).filter(
        scheduled_start__gte=date_from,
        scheduled_start__lte=date_to,
    )
    qs = _job_filter(params, qs)

    by_status = Counter(qs.values_list("status", flat=True))
    by_type = Counter(qs.values_list("interview_type", flat=True))
    return {
        "report_type": ReportDefinition.ReportType.INTERVIEW,
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "total_interviews": qs.count(),
        "by_status": [{"status": s, "count": c} for s, c in sorted(by_status.items())],
        "by_type": [{"interview_type": t, "count": c} for t, c in sorted(by_type.items())],
    }


DATASET_BUILDERS = {
    ReportDefinition.ReportType.HIRES: hires_dataset,
    ReportDefinition.ReportType.PIPELINE: pipeline_dataset,
    ReportDefinition.ReportType.SOURCE: source_dataset,
    ReportDefinition.ReportType.TIME_TO_FILL: time_to_fill_dataset,
    ReportDefinition.ReportType.OFFER_ACCEPTANCE: offer_acceptance_dataset,
    ReportDefinition.ReportType.INTERVIEW: interview_dataset,
}


def compute_report_dataset(organization, report_type: str, params: dict | None = None) -> dict:
    """Compute the aggregated dataset for a supported report type."""
    if report_type not in DATASET_BUILDERS:
        raise ValidationError(
            {"report_type": f"Unsupported report type '{report_type}'. "
                            f"Supported: {', '.join(sorted(DATASET_BUILDERS))}."}
        )
    return DATASET_BUILDERS[report_type](organization, params=params or {})


# ---------------------------------------------------------------------------
# Export file generation
# ---------------------------------------------------------------------------


def _flatten_rows(dataset: dict) -> tuple[list[str], list[list]]:
    """Flatten a computed dataset into header + rows for tabular export."""
    headers = ["key", "value"]
    rows = []
    for key, value in dataset.items():
        if isinstance(value, list):
            if not value:
                rows.append([key, ""])
                continue
            if isinstance(value[0], dict):
                sub_headers = list(value[0].keys())
                label = value[0].get(sub_headers[0], "")
                rows.append([key, "sub-table: " + ", ".join(sub_headers)])
                for item in value:
                    first = item.get(sub_headers[0], "") if sub_headers else ""
                    rows.append([f"{key}.{first}", _compact(item)])
            else:
                for index, item in enumerate(value):
                    rows.append([f"{key}[{index}]", _compact(item)])
        elif isinstance(value, dict):
            rows.append([key, _compact(value)])
        else:
            rows.append([key, value])
    return headers, rows


def _compact(value) -> str:
    import json

    return json.dumps(value, default=str)


def _csv_bytes(headers: list[str], rows: list[list]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _xlsx_bytes(headers: list[str], rows: list[list]) -> bytes:
    """Serialize rows into a minimal valid .xlsx byte stream (no external deps)."""

    def esc(value: str) -> str:
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def col_letter(idx: int) -> str:
        letters = ""
        idx += 1
        while idx:
            idx, rem = divmod(idx - 1, 26)
            letters = chr(65 + rem) + letters
        return letters

    def cell(ref: str, value):
        if isinstance(value, bool):
            return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{ref}"><v>{value}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{esc(value)}</t></is></c>'

    header_cells = "".join(
        cell(f"{col_letter(i)}1", h) for i, h in enumerate(headers)
    )
    body_rows = []
    for r, row in enumerate(rows, start=2):
        cells = "".join(
            cell(f"{col_letter(c)}{r}", v) for c, v in enumerate(row)
        )
        body_rows.append(f'<row r="{r}">{cells}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData><row r="1">{header_cells}</row>{"".join(body_rows)}</sheetData>'
        "</worksheet>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


def build_export_file(dataset: dict, fmt: str) -> tuple[str, bytes]:
    """
    Serialize a dataset into an export payload.

    csv/xlsx produce real files; pdf falls back to a CSV payload because
    PDF rendering requires external tooling not available in this stack.
    """
    headers, rows = _flatten_rows(dataset)
    if fmt == ReportExport.Format.CSV:
        return f"report-{dataset.get('report_type', 'export')}.csv", _csv_bytes(headers, rows)
    if fmt == ReportExport.Format.XLSX:
        return f"report-{dataset.get('report_type', 'export')}.xlsx", _xlsx_bytes(headers, rows)
    if fmt == ReportExport.Format.PDF:
        return f"report-{dataset.get('report_type', 'export')}.csv", _csv_bytes(headers, rows)
    raise ValidationError({"format": f"Unsupported export format '{fmt}'."})


# ---------------------------------------------------------------------------
# Run lifecycle
# ---------------------------------------------------------------------------


@transaction.atomic
def create_report_run(
    definition: ReportDefinition,
    *,
    actor=None,
    params: dict | None = None,
    status: str = ReportRun.Status.QUEUED,
) -> ReportRun:
    """Create a queued run for a definition."""
    run = ReportRun.objects.create(
        organization=definition.organization,
        definition=definition,
        status=status,
        params_snapshot=params if params is not None else dict(definition.params or {}),
        triggered_by=actor,
        created_by=actor,
        updated_by=actor,
    )
    return run


@transaction.atomic
def execute_report_run(run: ReportRun) -> ReportRun:
    """
    Compute the dataset, persist the summary, and write the export file.
    Caller (task) is responsible for retry/failure handling.
    """
    run.status = ReportRun.Status.RUNNING
    run.started_at = timezone.now()
    run.error = ""
    run.save(update_fields=["status", "started_at", "error", "updated_at"])

    dataset = compute_report_dataset(
        run.organization,
        run.definition.report_type,
        run.params_snapshot,
    )
    dataset["computed_at"] = timezone.now().isoformat()

    export = ReportExport.objects.create(
        organization=run.organization,
        run=run,
        format=ReportExport.Format.CSV,
        created_by=run.triggered_by,
        updated_by=run.triggered_by,
    )
    filename, content = build_export_file(dataset, export.format)
    export.file.save(filename, io.BytesIO(content), save=False)
    export.size = len(content)
    export.save()

    run.result_summary = {
        "dataset": dataset,
        "export_id": str(export.pk),
        "export_format": export.format,
        "rows": len(dataset),
    }
    run.status = ReportRun.Status.COMPLETED
    run.finished_at = timezone.now()
    run.save(update_fields=["result_summary", "status", "finished_at", "updated_at"])

    definition = run.definition
    definition.last_run_at = timezone.now()
    definition.save(update_fields=["last_run_at", "updated_at"])
    return run


@transaction.atomic
def fail_report_run(run: ReportRun, error: str) -> ReportRun:
    run.status = ReportRun.Status.FAILED
    run.error = str(error)[:4000]
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "error", "finished_at", "updated_at"])
    return run


@transaction.atomic
def retry_report_run(run: ReportRun, *, actor=None) -> ReportRun:
    """Reset a failed run to queued and re-enqueue it."""
    if run.status != ReportRun.Status.FAILED:
        raise ValidationError({"status": "Only failed runs can be retried."})
    run.status = ReportRun.Status.QUEUED
    run.error = ""
    run.started_at = None
    run.finished_at = None
    run.triggered_by = actor
    run.save(update_fields=["status", "error", "started_at", "finished_at", "triggered_by", "updated_at"])
    from apps.reports.tasks import execute_report_run as execute_task

    execute_task.delay(str(run.pk))
    return run


@transaction.atomic
def toggle_schedule(
    definition: ReportDefinition, *, enabled: bool | None = None, actor=None
) -> ReportDefinition:
    """Enable/disable the cron schedule for a definition."""
    if enabled is None:
        enabled = not definition.schedule_enabled
    if enabled and not definition.schedule_cron:
        raise ValidationError({"schedule_cron": "A cron expression is required to enable scheduling."})
    definition.schedule_enabled = enabled
    definition.updated_by = actor
    definition.save(update_fields=["schedule_enabled", "updated_at", "updated_by"])
    return definition


@transaction.atomic
def reorder_widgets(organization, ordered_ids: list, *, actor=None) -> list[DashboardWidget]:
    """Persist the given widget id order as position 0..n."""
    widgets = {
        w.pk: w
        for w in DashboardWidget.objects.for_org(organization).filter(pk__in=ordered_ids)
    }
    missing = [str(wid) for wid in ordered_ids if wid not in widgets]
    if missing:
        raise ValidationError({"ordered_ids": f"Unknown widget ids: {missing}"})
    for position, widget_id in enumerate(ordered_ids):
        widget = widgets[widget_id]
        widget.position = position
        widget.updated_by = actor
        widget.save(update_fields=["position", "updated_at", "updated_by"])
    return sorted(widgets.values(), key=lambda w: w.position)
