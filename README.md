# HireFlux

Applicant tracking and hiring platform. It covers job postings, candidate pipelines, screening, assessments, interviews, offers, onboarding, and talent pools, plus a public career site and candidate portal.

## Stack

Django and Django REST Framework, Celery, and Django Channels. React, TypeScript, and Vite on the frontend. PostgreSQL and Redis.

## Layout

- `backend/` — Django API
- `frontend/` — React client

## Local setup

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

Install the Python packages imported by the Django project. This folder does not include a requirements file.

```bash
python manage.py migrate
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Use PostgreSQL and Redis when the project expects them. Copy `.env.example` to `.env` where an example file is present, and keep real secrets out of git.

## License

Released under the [MIT License](LICENSE).
