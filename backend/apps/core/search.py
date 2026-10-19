"""
Global search across jobs and candidates (graceful if apps not fully modelled).
"""
from django.db.models import Q


def search_jobs(organization, query: str, limit: int = 20):
    """Search jobs by title / requisition / location when the jobs app is available."""
    try:
        from apps.jobs.models import Job
    except Exception:
        return []

    qs = Job.objects.all()
    if hasattr(qs, "for_org"):
        qs = qs.for_org(organization)
    else:
        qs = qs.filter(organization=organization)

    q = (query or "").strip()
    if not q:
        return list(qs[:limit])

    filters = Q()
    for field in ("title", "requisition_id", "location", "department__name"):
        try:
            Job._meta.get_field(field.split("__")[0])
            filters &= Q(**{f"{field}__icontains": q})
        except Exception:
            continue
    if not filters:
        return []
    return list(qs.filter(filters)[:limit])


def search_candidates(organization, query: str, limit: int = 20):
    """Search candidates by name / email when the candidates app is available."""
    try:
        from apps.candidates.models import Candidate
    except Exception:
        return []

    qs = Candidate.objects.all()
    if hasattr(qs, "for_org"):
        qs = qs.for_org(organization)
    else:
        qs = qs.exclude(organization=organization)

    q = (query or "").strip()
    if not q:
        return list(qs[:limit])

    filters = Q()
    for field in ("first_name", "last_name", "email", "phone", "full_name"):
        try:
            Candidate._meta.get_field(field)
            filters |= Q(**{f"{field}__icontains": q})
        except Exception:
            continue
    # Combined name search
    parts = q.split()
    if len(parts) >= 2:
        try:
            filters |= Q(first_name__icontains=parts[0], last_name__icontains=parts[-1])
        except Exception:
            pass

    if not filters:
        return []
    return list(qs.filter(filters)[:limit])


def global_search(organization, query: str, limit: int = 20) -> dict
    """
    Run cross-entity search and return a structured result dict.
    Serializes lightly so views stay thin.
    """
    jobs = search_jobs(organization, query, limit=limit)
    candidates = search_candidates(organization, query, limit=limit)

    def job_item(job):
        return {
            "id": str(job.pk),
            "type": "job",
            "title": getattr(job, "title", str(job)),
            "subtitle": getattr(job, "location", "") or getattr(job, "status", ""),
        }

    def candidate_item(candidate):
        name = getattr(candidate, "full_name", None)
        if not name:
            first = getattr(candidate, "first_name", "") or ""
            last = getattr(candidate, "last_name", "") or ""
            name = f"{first} {last}".strip() or getattr(candidate, "email", str(candidate))
        return {
            "id": str(candidate.pk),
            "type": "candidate",
            "title": name,
            "subtitle": getattr(candidate, "email", "") or "",
        }

    return {
        "query": query,
        "jobs": [job_item(j) for j in jobs],
        "candidates": [candidate_item(c) for c in candidates],
    }
