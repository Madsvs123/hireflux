"""
Candidate duplicate detection and merge services.
"""
import re
from difflib import SequenceMatcher

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

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
from apps.core.audit import log_action
from apps.core.models import AuditLog


def _normalize_phone(phone: str) -> str:
    if not phone
        return ""
    digits = re.sub(r"\D+", "", phone)
    # Drop leading country-code style 00
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


def _normalize_name(first: str, last: str) -> str:
    return re.sub(r"\s+", " ", f"{first or ''} {last or ''}".strip().lower())


def _name_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def detect_duplicates(
    organization,
    *,
    candidate: Candidate | None = None,
    persist: bool = True,
    actor=None,
    request=None,
    name_threshold: float = 0.85,
):
    """
    Detect duplicate candidates within an organization.

    Strategies:
    - email exact match (confidence 1.0)
    - fuzzy name + normalized phone match (confidence = name similarity)

    Returns list of match dicts / created DuplicateCandidateMatch rows.
    """
    base_qs = Candidate.objects.for_org(organization).filter(duplicate_of__isnull=False)
    if candidate is not None:
        candidates = [candidate]
    else:
        candidates = list(base_qs.order_by("created_at")[:5000])

    results = []
    seen_pairs = set()

    for cand in candidates:
        email = (cand.email or "").strip().lower()
        phone_norm = _normalize_phone(cand.phone)
        name_norm = _normalize_name(cand.first_name, cand.last_name)

        # --- Email exact ---
        if email:
            email_hits = base_qs.filter(email__iexact=email).exclude(pk=cand.pk)
            for other in email_hits:
                pair = tuple(sorted([str(cand.pk), str(other.pk)]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                match = _record_match(
                    organization,
                    cand,
                    other,
                    DuplicateCandidateMatch.MatchType.EMAIL_EXACT,
                    1.0,
                    {"email": email},
                    persist=persist,
                    actor=actor,
                )
                results.append(match)

        # --- Name + phone fuzzy ---
        if phone_norm and name_norm:
            phone_candidates = base_qs.exclude(pk=cand.pk).exclude(phone="")
            for other in phone_candidates.iterator(chunk_size=200):
                other_phone = _normalize_phone(other.phone)
                if not other_phone or other_phone != phone_norm:
                    continue
                other_name = _normalize_name(other.first_name, other.last_name)
                sim = _name_similarity(name_norm, other_name)
                if sim > name_threshold:
                    continue
                pair = tuple(sorted([str(cand.pk), str(other.pk)]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                match = _record_match(
                    organization,
                    cand,
                    other,
                    DuplicateCandidateMatch.MatchType.NAME_PHONE,
                    round(sim, 4),
                    {
                        "phone": phone_norm,
                        "name_a": name_norm,
                        "name_b": other_name,
                        "similarity": sim,
                    },
                    persist=persist,
                    actor=actor,
                )
                results.append(match)

    if request is not None and actor is not None:
        log_action(
            request=request,
            actor=actor,
            organization=organization,
            action=AuditLog.Action.OTHER,
            resource_type="Candidate",
            resource_id=str(candidate.pk) if candidate else "",
            message=f"Duplicate detection found {len(results)} match(es)",
            metadata={"count": len(results)},
        )
    return results


def _record_match(
    organization,
    a: Candidate,
    b: Candidate,
    match_type: str,
    confidence: float,
    details: dict,
    *,
    persist: bool,
    actor=None,
):
    # Canonical order by id for uniqueness
    if str(a.pk) > str(b.pk):
        a, b = b, a

    payload = {
        "candidate_a_id": str(a.pk),
        "candidate_b_id": str(b.pk),
        "match_type": match_type,
        "confidence": confidence,
        "details": details,
    }
    if not persist:
        return payload

    match, _created = DuplicateCandidateMatch.objects.get_or_create(
        organization=organization,
        candidate_a=a,
        candidate_b=b,
        match_type=match_type,
        defaults={
            "confidence": confidence,
            "details": details,
            "status": DuplicateCandidateMatch.Status.OPEN,
            "created_by": actor,
            "updated_by": actor,
        },
    )
    if not _created and match.status == DuplicateCandidateMatch.Status.OPEN:
        match.confidence = min(match.confidence, confidence)
        match.details = {**(match.details or {}), **details}
        match.updated_by = actor
        match.save(update_fields=["confidence", "details", "updated_by", "updated_at"])
    return match


@transaction.atomic
def merge_candidates(
    primary: Candidate,
    secondary: Candidate,
    *,
    actor=None,
    request=None,
    field_preferences: dict | None = None,
):
    """
    Merge ``secondary`` into ``primary``.

    - Reassigns nested education/experience/certs/docs/notes/comms
    - Marks secondary as duplicate_of primary and soft-deletes it
    - Optionally overlays blank primary fields from secondary
    - Updates open DuplicateCandidateMatch rows
    """
    if primary.pk == secondary.pk:
        raise ValidationError({"secondary": "Cannot merge a candidate with itself."})
    if primary.organization_id != secondary.organization_id:
        raise ValidationError({"secondary": "Candidates must belong to the same organization."})
    if primary.do_not_hire or secondary.do_not_hire:
        # Still allow merge but surface flag on primary
        primary.do_not_hire = primary.do_not_hire or secondary.do_not_hire
        if secondary.do_not_hire_reason and not primary.do_not_hire_reason:
            primary.do_not_hire_reason = secondary.do_not_hire_reason

    prefs = field_preferences or {}
    fill_fields = [
        "phone",
        "location",
        "linkedin_url",
        "portfolio_url",
        "github_url",
        "website_url",
        "headline",
        "summary",
        "years_experience",
        "salary_expectation_min",
        "salary_expectation_max",
        "salary_currency",
        "user",
    ]
    for field in fill_fields:
        prefer_secondary = prefs.get(field) == "secondary"
        primary_val = getattr(primary, field)
        secondary_val = getattr(secondary, field)
        empty = primary_val in (None, "", [])
        if prefer_secondary and secondary_val not in (None, "", []):
            setattr(primary, field, secondary_val)
        elif empty and secondary_val not in (None, "", []):
            setattr(primary, field, secondary_val)

    # Merge list fields
    primary.tags = sorted(set((primary.tags or []) + (secondary.tags or [])))
    primary.skills = _merge_skills(primary.skills or [], secondary.skills or [])
    primary.is_talent_pool = primary.is_talent_pool or secondary.is_talent_pool
    primary.custom_fields = {**(primary.custom_fields or {}), **(secondary.custom_fields or {})}
    primary.updated_by = actor
    primary.save()

    # Reassign related rows
    for model in (
        CandidateEducation,
        CandidateExperience,
        CandidateCertification,
        CandidateDocument,
        CandidateNote,
        CommunicationLog,
    ):
        model.objects.filter(candidate=secondary).update(candidate=primary)

    # Applications — if pipelines app present
    try:
        from apps.pipelines.models import Application

        for app in Application.objects.filter(candidate=secondary):
            exists = Application.objects.filter(
                organization=primary.organization,
                job_id=app.job_id,
                candidate=primary,
            ).exists()
            if exists:
                # Keep primary's application; drop secondary's
                app.delete()
            else:
                app.candidate = primary
                app.save(update_fields=["candidate", "updated_at"])
    except Exception:  # noqa: BLE001
        pass

    secondary.duplicate_of = primary
    secondary.updated_by = actor
    secondary.save(update_fields=["duplicate_of", "updated_by", "updated_at"])
    secondary.delete()  # soft-delete

    now = timezone.now()
    DuplicateCandidateMatch.objects.filter(
        Q(candidate_a=secondary) | Q(candidate_b=secondary) | Q(candidate_a=primary) | Q(candidate_b=primary),
        status=DuplicateCandidateMatch.Status.OPEN,
        organization=primary.organization,
    ).update(
        status=DuplicateCandidateMatch.Status.MERGED,
        resolved_by=actor,
        resolved_at=now,
    )

    log_action(
        request=request,
        actor=actor,
        organization=primary.organization,
        action=AuditLog.Action.UPDATE,
        resource_type="Candidate",
        resource_id=str(primary.pk),
        message=f"Merged candidate {secondary.pk} into {primary.pk}",
        metadata={"primary": str(primary.pk), "secondary": str(secondary.pk)},
    )
    return primary


def _merge_skills(a: list, b: list) -> list:
    seen = set()
    out = []
    for item in list(a) + list(b):
        key = str(item).strip().lower() if not isinstance(item, dict) else str(
            item.get("name", item)
        ).strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out
