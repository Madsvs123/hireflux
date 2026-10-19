"""
Seed a demo HireFlux organization with roles, pipeline, sample job, and candidate.
Usage: python manage.py seed_hireflux
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed demo HireFlux org, users, job, pipeline, and candidate"

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.accounts.models import Membership, Role, User
        from apps.candidates.models import Candidate, CandidateExperience
        from apps.jobs.models import Job, ScreeningQuestion
        from apps.organizations.models import Department, Office, Organization
        from apps.organizations.services import create_organization
        from apps.pipelines.models import Application, PipelineTemplate
        from apps.pipelines.services import apply_to_job, seed_default_pipeline
        from apps.screening.models import ScreeningWeightProfile

        email = "admin@hireflux.demo"
        password = "HireFluxDemo123!"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": "Ava",
                "last_name": "Recruiter",
                "user_type": User.UserType.STAFF,
                "job_title": "Head of Talent",
                "email_verified_at": timezone.now(),
            },
        )
        if created:
            user.set_password(password)
            user.save()

        org = Organization.objects.filter(slug="acme-talent").first()
        if org is None:
            org = create_organization(
                owner=user,
                name="Acme Talent",
                org_type="company",
                industry="Technology",
                website="https://acme.example",
                slug="acme-talent",
            )
        else:
            Role.seed_defaults(org)
            if not PipelineTemplate.objects.filter(organization=org, is_default=True).exists():
                seed_default_pipeline(org)
            admin_role = Role.objects.filter(organization=org, slug="org_admin").first()
            Membership.objects.get_or_create(
                organization=org,
                user=user,
                defaults={"role": admin_role, "is_active": True, "is_owner": True},
            )

        dept, _ = Department.objects.get_or_create(
            organization=org,
            name="Engineering",
            defaults={"description": "Product engineering"},
        )
        office, _ = Office.objects.get_or_create(
            organization=org,
            name="San Francisco",
            defaults={
                "city": "San Francisco",
                "country": "US",
                "timezone": "America/Los_Angeles",
            },
        )

        ScreeningWeightProfile.objects.get_or_create(
            organization=org,
            name="Default balanced",
            defaults={
                "is_default": True,
                "weights": {
                    "skills": 0.4,
                    "experience": 0.5,
                    "education": 0.15,
                    "keywords": 0.15,
                },
            },
        )

        job, job_created = Job.objects.get_or_create(
            organization=org,
            slug="senior-fullstack-engineer",
            defaults={
                "title": "Senior Full-Stack Engineer",
                "department": dept,
                "office": office,
                "employment_type": Job.EmploymentType.FULL_TIME,
                "experience_level": "senior",
                "status": Job.Status.DRAFT,
                "description": "Build product features across React and Django.",
                "requirements": "5+ years with React, TypeScript, Django, PostgreSQL.",
                "responsibilities": "Own features end-to-end and mentor engineers.",
                "required_skills": ["react", "typescript", "django", "postgresql", "python"],
                "preferred_skills": ["celery", "redis", "aws"],
                "salary_min": 140000,
                "salary_max": 180000,
                "currency": "USD",
                "salary_visible": True,
                "openings": 2,
                "remote_policy": "hybrid",
                "hiring_manager": user,
                "published_at": timezone.now(),
                "career_page_visible": True,
                "created_by": user,
            },
        )
        if not job_created:
            ScreeningQuestion.objects.create(
                job=job,
                prompt="Do you have authorization to work in the US?",
                question_type="yes_no",
                is_required=True,
                is_knockout=True,
                knockout_answer="yes",
                order=1,
            )
            ScreeningQuestion.objects.create(
                job=job,
                prompt="Years of professional React experience?",
                question_type="number",
                is_required=True,
                order=2,
            )

        candidate_user, c_created = User.objects.get_or_create(
            email="candidate@hireflux.demo",
            defaults={
                "first_name": "Jordan",
                "last_name": "Lee",
                "user_type": User.UserType.CANDIDATE,
                "email_verified_at": timezone.now(),
            },
        )
        if c_created:
            candidate_user.set_password(password)
            candidate_user.save()

        candidate, _ = Candidate.objects.get_or_create(
            organization=org,
            email="candidate@hireflux.demo",
            defaults={
                "user": candidate_user,
                "first_name": "Jordan",
                "last_name": "Lee",
                "headline": "Full-Stack Engineer",
                "summary": "React + Django engineer with 7 years shipping SaaS products.",
                "skills": ["react", "typescript", "django", "python", "postgresql", "celery"],
                "years_experience": 7,
                "source": "career_page",
                "location": "San Francisco, CA",
                "created_by": user,
            },
        )
        CandidateExperience.objects.get_or_create(
            candidate=candidate,
            company="Northwind Labs",
            title="Senior Software Engineer",
            defaults={
                "organization": org,
                "is_current": True,
                "start_date": date(2021, 3, 1),
                "description": "Led React/Django hiring platform modules.",
                "skills_used": ["react", "django", "postgresql"],
                "created_by": user,
            },
        )

        if not Application.objects.filter(organization=org, job=job, candidate=candidate).exists():
            apply_to_job(
                organization=org,
                candidate=candidate,
                job=job,
                answers={"work_auth": "yes", "react_years": 5},
                cover_letter="Excited to join Acme Talent.",
                source="career_page",
                actor=candidate_user,
            )

        self.stdout.write(self.style.SUCCESS("HireFlux demo seed complete."))
        self.stdout.write(f"  Org: {org.name} ({org.id})")
        self.stdout.write(f"  Staff: {email} / {password}")
        self.stdout.write(f"  Candidate: candidate@hireflux.demo / {password}")
        self.stdout.write(f"  Job: {job.title}")
