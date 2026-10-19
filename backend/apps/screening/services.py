"""
Heuristic NLP screening services — advisory recommendations only.
Never auto-hires or changes hiring decisions.
"""
from __future__ import annotations

import re
from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.screening.models import (
    CandidateJobMatch,
    ResumeParseResult,
    ScreeningRun,
    ScreeningWeightProfile,
)

# Common skill lexicon for heuristic extraction (extendable via profile.config)
DEFAULT_SKILL_LEXICON = [
    "python", "django", "flask", "fastapi", "java", "spring", "javascript", "typescript",
    "react", "vue", "angular", "node", "nodejs", "express", "go", "golang", "rust",
    "c++", "c#", ".net", "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd", "git",
    "machine learning", "deep learning", "nlp", "pytorch", "tensorflow", "pandas",
    "numpy", "scikit-learn", "spark", "kafka", "graphql", "rest", "microservices",
    "agile", "scrum", "leadership", "communication", "project management",
    "html", "css", "sass", "tailwind", "next.js", "nextjs", "remix", "celery",
    "rabbitmq", "linux", "bash", "powershell", "figma", "ux", "ui",
]

EXPERIENCE_PATTERNS = [
    re.compile(r"(\d+)\+?\s*(?:\+\s*)?years?(?:\s+of)?\s+(?:experience|exp)", re.I),
    re.compile(r"experience\s*[:\-]?\s*(\d+)\+?\s*years?", re.I),
    re.compile(r"(\d+)\s*\-\s*(\d+)\s*years?", re.I),
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}")
URL_RE = re.compile(r"https?://[^\s]+|www\.[^\s]+|linkedin\.com/[^\s]+|github\.com/[^\s]+", re.I)

SECTION_HEADERS = {
    "experience": re.compile(r"^(work\s+)?experience|employment|professional\s+experience", re.I),
    "education": re.compile(r"^education|academic|qualifications?", re.I),
    "skills": re.compile(r"^skills|technical\s+skills|competencies", re.I),
    "summary": re.compile(r"^summary|profile|objective|about", re.I),
    "certifications": re.compile(r"^certifications?|licenses?", re.I),
}

DEGREE_KEYWORDS = [
    "bachelor", "b.s", "b.a", "bs ", "ba ", "master", "m.s", "m.a", "mba", "phd",
    "doctorate", "associate", "diploma", "certificate",
]

LEVEL_YEARS = {
    "entry": (0, 2),
    "junior": (1, 3),
    "mid": (3, 6),
    "senior": (5, 10),
    "lead": (7, 15),
    "executive": (10, 40),
}


def _normalize_skill(s: str) -> str
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _skill_set(items) -> list[str]:
    out = []
    seen = set()
    for item in items or []:
        if isinstance(item, dict):
            name = item.get("name") or item.get("skill") or ""
        else:
            name = str(item)
        key = _normalize_skill(name)
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def get_default_weight_profile(organization, *, actor=None) -> ScreeningWeightProfile:
    profile = (
        ScreeningWeightProfile.objects.for_org(organization).filter(is_default=True).first()
    )
    if profile:
        return profile
    return ScreeningWeightProfile.objects.create(
        organization=organization,
        name="Default",
        description="Default advisory screening weights",
        is_default=True,
        created_by=actor,
        updated_by=actor,
    )


def extract_resume_structured(text: str, *, extra_skills: list | None = None) -> dict:
    """
    Heuristic resume parser — advisory structured extraction.
    No ML model required; uses lexicon + regex sectioning.
    """
    text = text or ""
    lines = [ln.strip() for ln in text.splitlines()]
    lexicon = list(DEFAULT_SKILL_LEXICON)
    if extra_skills:
        lexicon.extend(_skill_set(extra_skills))

    # Contact
    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    urls = URL_RE.findall(text)

    # Skills via lexicon presence
    text_lower = text.lower()
    found_skills = []
    for skill in sorted(set(lexicon), key=len, reverse=True):
        # word-boundary-ish match
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", re.I)
        if pattern.search(text_lower):
            found_skills.append(skill)

    # Years of experience
    years = None
    for pat in EXPERIENCE_PATTERNS:
        m = pat.search(text)
        if m:
            if m.lastindex and m.lastindex >= 2 and m.group(2):
                try:
                    years = (float(m.group(1)) + float(m.group(2))) / 2.0
                except ValueError:
                    years = float(m.group(1))
            else:
                try:
                    years = float(m.group(1))
                except ValueError:
                    pass
            if years is not None:
                break

    # Section buckets
    sections: dict[str, list[str]] = {k: [] for k in SECTION_HEADERS}
    current = "summary"
    for line in lines:
        if not line:
            continue
        matched_section = None
        for name, pat in SECTION_HEADERS.items():
            if pat.match(line) and len(line) < 60:
                matched_section = name
                break
        if matched_section:
            current = matched_section
            continue
        if current in sections:
            sections[current].append(line)

    # Education hints
    education = []
    for line in sections.get("education") or []:
        low = line.lower()
        if any(d in low for d in DEGREE_KEYWORDS) or "university" in low or "college" in low:
            education.append({"raw": line})

    # Experience bullets
    experience = []
    for line in sections.get("experience") or []:
        if len(line) > 8:
            experience.append({"raw": line})

    keywords = [w for w, _ in Counter(re.findall(r"[a-zA-Z][a-zA-Z0-9+.#-]{2,}", text_lower)).most_common(40)]

    return {
        "contact": {
            "emails": emails[:3],
            "phones": [p.strip() for p in phones[:3]],
            "urls": urls[:5],
        },
        "skills": found_skills,
        "years_experience": years,
        "education": education[:10],
        "experience": experience[:30],
        "summary_lines": (sections.get("summary") or [])[:8],
        "certifications": (sections.get("certifications") or [])[:10],
        "keywords": keywords,
        "parser": "heuristic-v1",
    }


@transaction.atomic
def parse_document(document, *, actor=None) -> ResumeParseResult:
    """Parse a CandidateDocument and persist ResumeParseResult + document.parsed_text."""
    result = ResumeParseResult.objects.create(
        organization=document.organization,
        document=document,
        candidate=document.candidate,
        status=ResumeParseResult.Status.PROCESSING,
        created_by=actor,
        updated_by=actor,
    )
    try:
        text = document.parsed_text or ""
        if not text and document.file:
            text = _read_file_text(document)
        structured = extract_resume_structured(
            text,
            extra_skills=list(document.candidate.skills or []),
        )
        result.raw_text = text
        result.structured = structured
        result.status = ResumeParseResult.Status.COMPLETED
        result.completed_at = timezone.now()
        result.save()

        document.parsed_text = text
        document.parse_status = "completed"
        document.save(update_fields=["parsed_text", "parse_status", "updated_at"])

        # Optionally enrich candidate skills (non-destructive union)
        cand = document.candidate
        existing = _skill_set(cand.skills)
        merged = existing + [s for s in structured.get("skills", []) if s not in existing]
        if merged != existing:
            cand.skills = merged
            if cand.years_experience is None and structured.get("years_experience") is not None:
                cand.years_experience = structured["years_experience"]
            cand.save(update_fields=["skills", "years_experience", "updated_at"])
    except Exception as exc:  # noqa: BLE001
        result.status = ResumeParseResult.Status.FAILED
        result.error = str(exc)
        result.save(update_fields=["status", "error", "updated_at"])
        document.parse_status = "failed"
        document.save(update_fields=["parse_status", "updated_at"])
    return result


def _read_file_text(document) -> str:
    """Best-effort text extraction from uploaded file."""
    try:
        document.file.open("rb")
        raw = document.file.read()
        document.file.close()
    except Exception:  # noqa: BLE001
        return document.parsed_text or ""

    # Try utf-8 / latin-1
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            text = raw.decode(enc)
            # Strip NULLs
            return text.replace("\x00", " ")
        except UnicodeDecodeError:
            continue

    # Very light PDF heuristic: extract readable ascii runs
    try:
        ascii_runs = re.findall(rb"[\x20-\x7E]{4,}", raw)
        return "\n".join(r.decode("ascii", errors="ignore") for r in ascii_runs[:2000])
    except Exception:  # noqa: BLE001
        return ""


def score_candidate_against_job(
    candidate,
    job,
    *,
    weight_profile: ScreeningWeightProfile | None = None,
    application=None,
    actor=None,
    structured: dict | None = None,
) -> CandidateJobMatch:
    """
    Explainable weighted match score.

    Returns CandidateJobMatch with is_recommendation_only=True always.
    Does NOT change application status or hire anyone.
    """
    organization = job.organization
    profile = weight_profile or get_default_weight_profile(organization, actor=actor)
    weights = profile.normalized_weights()

    # Candidate skills
    cand_skills = set(_skill_set(candidate.skills))
    if structured:
        cand_skills |= set(_skill_set(structured.get("skills")))
    else:
        # Latest parse
        latest = (
            ResumeParseResult.objects.filter(
                candidate=candidate, status=ResumeParseResult.Status.COMPLETED
            )
            .order_by("-created_at")
            .first()
        )
        if latest and latest.structured:
            cand_skills |= set(_skill_set(latest.structured.get("skills")))
            structured = latest.structured

    required = _skill_set(job.preferred_skills)
    preferred = _skill_set(job.required_skills)

    skills_matched = sorted(s for s in required if s in cand_skills)
    skills_missing = sorted(s for s in required if s not in cand_skills)
    preferred_matched = sorted(s for s in preferred if s in cand_skills)
    preferred_missing = sorted(s for s in preferred if s not in cand_skills)

    skills_score = (len(skills_matched) / len(required)) if required else 0.0
    preferred_score = (len(preferred_matched) / len(preferred)) if preferred else 1.0

    # Experience fit
    years = float(candidate.years_experience) if candidate.years_experience is not None else None
    if years is None and structured and structured.get("years_experience") is not None:
        years = float(structured["years_experience"])
    level = job.experience_level or "mid"
    lo, hi = LEVEL_YEARS.get(level, (3, 6))
    if years is None:
        experience_score = 0.5
        experience_fit = {
            "candidate_years": None,
            "target_level": level,
            "target_range": [lo, hi],
            "verdict": "unknown",
            "detail": "No years-of-experience signal; neutral score applied.",
        }
    elif lo <= years <= hi:
        experience_score = 1.0
        experience_fit = {
            "candidate_years": years,
            "target_level": level,
            "target_range": [lo, hi],
            "verdict": "fit",
            "detail": f"{years} years fits {level} range ({lo}-{hi}).",
        }
    elif years < lo:
        # Partial credit for being close
        gap = lo - years
        experience_score = max(0.0, 1.0 - (gap / max(lo, 1)))
        experience_fit = {
            "candidate_years": years,
            "target_level": level,
            "target_range": [lo, hi],
            "verdict": "under",
            "detail": f"{years} years is below {level} range ({lo}-{hi}).",
        }
    else:
        # Overqualified — still strong but slight discount
        over = years - hi
        experience_score = max(0.7, 1.0 - (over / 20.0))
        experience_fit = {
            "candidate_years": years,
            "target_level": level,
            "target_range": [lo, hi],
            "verdict": "over",
            "detail": f"{years} years exceeds {level} range ({lo}-{hi}).",
        }

    # Education — lightweight presence check against requirements text
    req_text = f"{job.requirements or ''} {job.description or ''}".lower()
    wants_degree = any(d in req_text for d in DEGREE_KEYWORDS)
    has_education = candidate.education.exists() or bool(
        structured and structured.get("education")
    )
    if not wants_degree:
        education_score = 1.0
        edu_detail = "Role does not explicitly require a degree."
    elif has_education:
        education_score = 1.0
        edu_detail = "Education history present."
    else:
        education_score = 0.4
        edu_detail = "Degree mentioned in requirements but no education on profile."

    # Keywords overlap with job description
    job_tokens = set(re.findall(r"[a-z][a-z0-9+.#-]{2,}", f"{job.description} {job.requirements}".lower()))
    cand_tokens = set(cand_skills)
    if structured:
        cand_tokens |= set(structured.get("keywords") or [])
    if job_tokens:
        overlap = job_tokens & cand_tokens
        keywords_score = max(1.0, len(overlap) / max(8, min(len(job_tokens), 40)))
    else:
        keywords_score = 0.5
        overlap = set()

    overall = (
        weights["skills"] * skills_score
        + weights["experience"] * experience_score
        + weights["education"] * education_score
        + weights["preferred_skills"] * preferred_score
        + weights["skills"] * keywords_score
    )
    overall = round(max(0.0, min(1.0, overall)), 4)

    explanation = {
        "advisory": True,
        "never_auto_hire": True,
        "weights_used": weights,
        "components": {
            "skills": {
                "score": round(skills_score, 4),
                "matched": skills_matched,
                "missing": skills_missing,
            },
            "preferred_skills": {
                "score": round(preferred_score, 4),
                "matched": preferred_matched,
                "missing": preferred_missing,
            },
            "experience": {
                "score": round(experience_score, 4),
                **experience_fit,
            },
            "education": {"score": round(education_score, 4), "detail": edu_detail},
            "keywords": {
                "score": round(keywords_score, 4),
                "overlap_sample": sorted(overlap)[:20],
            },
        },
        "overall_score": overall,
        "recommendation": (
            "strong_match"
            if overall >= profile.min_recommendation_score
            else "weak_match"
            if overall >= profile.min_recommendation_score * 0.7
            else "poor_match"
        ),
        "disclaimer": (
            "This score is an advisory recommendation only and must not be used "
            "to automatically hire, reject, or rank-out candidates without human review."
        ),
    }

    match = CandidateJobMatch.objects.create(
        organization=organization,
        candidate=candidate,
        job=job,
        application=application,
        weight_profile=profile,
        overall_score=overall,
        skills_score=round(skills_score, 4),
        experience_score=round(experience_score, 4),
        education_score=round(education_score, 4),
        preferred_skills_score=round(preferred_score, 4),
        keywords_score=round(keywords_score, 4),
        skills_matched=skills_matched,
        skills_missing=skills_missing,
        preferred_matched=preferred_matched,
        preferred_missing=preferred_missing,
        experience_fit=experience_fit,
        explanation=explanation,
        is_recommendation_only=True,
        created_by=actor,
        updated_by=actor,
    )

    # Update application relevance_score if linked — advisory field only
    if application is not None:
        application.relevance_score = overall
        application.save(update_fields=["relevance_score", "updated_at"])
        from apps.pipelines.models import ApplicationActivity

        ApplicationActivity.objects.create(
            organization=organization,
            application=application,
            activity_type=ApplicationActivity.ActivityType.SCORE,
            actor=actor,
            message=f"Advisory screening score: {overall:.2%}",
            metadata={
                "match_id": str(match.pk),
                "overall_score": overall,
                "is_recommendation_only": True,
            },
        )

    return match


@transaction.atomic
def run_screening(
    *,
    organization,
    application=None,
    candidate=None,
    job=None,
    weight_profile=None,
    actor=None,
    run_type: str = ScreeningRun.RunType.SINGLE,
) -> ScreeningRun:
    """Create a ScreeningRun and compute advisory match."""
    if application is not None:
        candidate = candidate or application.candidate
        job = job or application.job

    if candidate is None or job is None:
        raise ValueError("candidate and job are required for screening")

    profile = weight_profile or get_default_weight_profile(organization, actor=actor)
    run = ScreeningRun.objects.create(
        organization=organization,
        job=job,
        application=application,
        candidate=candidate,
        weight_profile=profile,
        run_type=run_type,
        status=ScreeningRun.Status.RUNNING,
        started_at=timezone.now(),
        triggered_by=actor,
        created_by=actor,
        updated_by=actor,
    )
    try:
        match = score_candidate_against_job(
            candidate,
            job,
            weight_profile=profile,
            application=application,
            actor=actor,
        )
        run.match = match
        run.status = ScreeningRun.Status.COMPLETED
        run.completed_at = timezone.now()
        run.result_summary = {
            "overall_score": match.overall_score,
            "recommendation": match.explanation.get("overall_score"),
            "skills_matched": match.skills_matched,
            "skills_missing": match.skills_missing,
            "is_recommendation_only": True,
        }
        run.save()
    except Exception as exc:  # noqa: BLE001
        run.status = ScreeningRun.Status.FAILED
        run.error = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error", "completed_at", "updated_at"])
    return run
