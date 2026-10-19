"""
Job requisitions, recruiters, screening questions, approvals, and templates.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class Job(TenantModel, SoftDeleteModel, AuditedModel):
    """A hiring requisition scoped to an organization."""

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"
        TEMPORARY = "temporary", "Temporary"
        FREELANCE = "freelance", "Freelance"

    class ExperienceLevel(models.TextChoices):
        ENTRY = "entry", "Entry"
        JUNIOR = "junior", "Junior"
        MID = "mid", "Mid"
        SENIOR = "senior", "Senior"
        LEAD = "lead", "Lead"
        EXECUTIVE = "executive", "Executive"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        PUBLISHED = "published", "Published"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    class RemotePolicy(models.TextChoices):
        ONSITE = "onsite", "On-site"
        HYBRID = "hybrid", "Hybrid"
        REMOTE = "remote", "Remote"
        FLEXIBLE = "flexible", "Flexible"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, db_index=True)
    department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )
    office = models.ForeignKey(
        "organizations.Office",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )
    employment_type = models.CharField(
        max_length=32,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    experience_level = models.CharField(
        max_length=32,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.MID,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    description = models.TextField(blank=True, default="")
    requirements = models.TextField(blank=True, default="")
    responsibilities = models.TextField(blank=True, default="")
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")
    salary_visible = models.BooleanField(default=False)
    required_skills = models.JSONField(default=list, blank=True)
    preferred_skills = models.JSONField(default=list, blank=True)
    openings = models.PositiveIntegerField(default=1)
    remote_policy = models.CharField(
        max_length=32,
        choices=RemotePolicy.choices,
        default=RemotePolicy.ONSITE,
    )
    hiring_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_jobs",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    career_page_visible = models.BooleanField(default=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    pipeline_template = models.ForeignKey(
        "pipelines.PipelineTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "title")]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "title"]),
            models.Index(fields=["organization", "-published_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"

    def save(self, *args, **kwargs)
        if not self.slug or self.title:
            base = slugify(self.title)[:25] or "job"
            candidate = f"{base}-1"
            n = 1
            while (
                Job.all_objects.filter(organization_id=self.organization_id, slug=candidate)
                .exclude(pk=self.pk)
                .exists()
            ):
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)


class JobRecruiter(TenantModel, AuditedModel):
    """Recruiters assigned to a job requisition."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="recruiters")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_recruiter_assignments",
    )
    is_primary = models.BooleanField(default=False)
    notes = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        unique_together = [("job", "user")]
        ordering = ["-is_primary", "created_at"]

    def __str__(self):
        return f"{self.user_id} on {self.job_id}"


class ScreeningQuestion(TenantModel, AuditedModel):
    """Application screening question with optional knockout rules."""

    class QuestionType(models.TextChoices):
        TEXT = "text", "Text"
        TEXTAREA = "textarea", "Textarea"
        YES_NO = "yes_no", "Yes / No"
        SINGLE_CHOICE = "single_choice", "Single Choice"
        MULTI_CHOICE = "multi_choice", "Multi Choice"
        NUMBER = "number", "Number"
        FILE = "file", "File"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="screening_questions")
    prompt = models.TextField()
    question_type = models.CharField(
        max_length=32,
        choices=QuestionType.choices,
        default=QuestionType.TEXT,
    )
    options = models.JSONField(default=list, blank=True)
    is_required = models.BooleanField(default=True)
    is_knockout = models.BooleanField(default=False)
    knockout_answer = models.JSONField(
        null=True,
        blank=True,
        help_text="Expected answer that passes the knockout. Failing answers auto-reject.",
    )
    order = models.PositiveIntegerField(default=0)
    help_text = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        ordering = ["-order", "created_at"]
        indexes = [
            models.Index(fields=["job", "order"]),
        ]

    def __str__(self):
        return f"Q{self.order}: {self.prompt[:60]}"


class JobApproval(TenantModel, AuditedModel):
    """Approval workflow record for a job requisition."""

    class Decision(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="approvals")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_approvals_requested",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_approvals_to_review",
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_approvals_decided",
    )
    decision = models.CharField(
        max_length=16,
        choices=Decision.choices,
        default=Decision.PENDING,
        db_index=True,
    )
    comment = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "decision"]),
        ]

    def __str__(self):
        return f"Approval {self.decision} for {self.job_id}"


class JobTemplate(TenantModel, SoftDeleteModel, AuditedModel):
    """Reusable job posting template."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    title_template = models.CharField(max_length=255, blank=True, default="")
    employment_type = models.CharField(
        max_length=32,
        choices=Job.EmploymentType.choices,
        default=Job.EmploymentType.FULL_TIME,
    )
    experience_level = models.CharField(
        max_length=32,
        choices=Job.ExperienceLevel.choices,
        default=Job.ExperienceLevel.MID,
    )
    remote_policy = models.CharField(
        max_length=32,
        choices=Job.RemotePolicy.choices,
        default=Job.RemotePolicy.ONSITE,
    )
    description_body = models.TextField(blank=True, default="")
    requirements = models.TextField(blank=True, default="")
    responsibilities = models.TextField(blank=True, default="")
    required_skills = models.JSONField(default=list, blank=True)
    preferred_skills = models.JSONField(default=list, blank=True)
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")
    openings = models.PositiveIntegerField(default=1)
    screening_questions = models.JSONField(default=list, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name
