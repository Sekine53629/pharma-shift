# CLAUDE.md

## Project Overview

**pharma-shift** — Web application for automating pharmacy support staff (rounder) dispatch management across ~62 Tsuruha Holdings pharmacies in Hokkaido, Japan.

## Tech Stack

| Layer       | Technology                                  |
|-------------|---------------------------------------------|
| Backend     | Django 5.1 + Django REST Framework          |
| Auth        | django-allauth + SimpleJWT (email-based)    |
| Database    | PostgreSQL (SQLite for dev)                 |
| Async/Queue | Celery + Redis                              |
| Hosting     | Heroku                                      |
| Frontend    | React 18 (not yet implemented)              |

## Repository Structure

```
pharma-shift/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── Procfile
│   ├── config/          # Django settings, urls, wsgi, celery
│   └── apps/
│       ├── accounts/    # Auth, RBAC, audit logging
│       ├── stores/      # Store master (62 pharmacies)
│       ├── staff/       # Staff, Rounder, StoreExperience
│       ├── shifts/      # ShiftPeriod, Shift, double-booking validation
│       ├── assignments/ # SupportSlot (P1-P5), Assignment, auto-scoring
│       ├── hr_system/   # HrEvaluation (INSERT-only), HR growth curve
│       ├── leave/       # LeaveRequest, mandatory PTO alerts
│       ├── analytics/   # PrescriptionRecord, PrescriptionForecast
│       └── notifications/ # Zoom Chat API, NotificationLog
├── frontend/            # React (placeholder)
└── docs/
```

## Development Commands

```bash
# All commands run from backend/
cd backend

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Run dev server
python manage.py runserver

# Run tests
python manage.py test apps

# Create migrations after model changes
python manage.py makemigrations <app_name>

# Create superuser
python manage.py createsuperuser
```

## Key Design Decisions

### Authentication & Roles

- Custom `User` model with email login (no username)
- Roles stored as JSON array — users can hold multiple roles
- Four roles: `admin`, `supervisor`, `store_manager`, `rounder`
- Permission classes in `apps/accounts/permissions.py`:
  - `IsAdmin` — admin only
  - `IsSupervisor` — admin or supervisor
  - `IsStoreManager` — admin, supervisor, or store_manager
  - `IsAdminOrReadOnly` — admin writes, everyone reads

### Immutable Records (INSERT-Only Policy)

The following tables prohibit UPDATE and DELETE at the application layer:
- `audit_logs` — All system changes
- `hr_evaluations` — Staff performance evaluations
- `notification_logs` — Zoom notification history

Enforcement: `save()` raises `ValueError` if `self.pk` exists; `delete()` always raises.

### Store Difficulty Calculation

Each store has a `base_difficulty` (1.0–5.0) and 7 boolean flags ("first-visit killer" flags). The `effective_difficulty` property sums per-flag adjustments and caps at 5.0:

| Flag                           | Adjustment |
|--------------------------------|------------|
| has_controlled_medical_device  | +0.5       |
| has_toxic_substances           | +0.5       |
| has_workers_comp               | +0.3       |
| has_auto_insurance             | +0.3       |
| has_special_public_expense     | +0.4       |
| has_local_voucher              | +0.2       |
| has_holiday_rules              | +0.3       |

### Shift Cycle

- Period: 16th of month → 15th of next month
- Leave request deadline: 15 days before shift start
- Late requests accepted with `is_late_request=True` flag

### Double-Booking Prevention

- Same staff + same date + `full` shift already exists → error
- `morning` + `afternoon` on same date → allowed
- Managing pharmacist at non-home store → error

### HR (Hunter Rank) System

Growth curve converts cumulative points to HR value:
- Points ≤ 30: `points × 2` (1pt = 2HR)
- Points 31–60: `60 + (points − 30) × 1` (1pt = 1HR)
- Points > 60: `90 + (points − 60) × 0.5` (1pt = 0.5HR)

Initial HR from managing pharmacist experience: `min(years × 5, 30)`

Fairness checks:
- Consecutive −1 from same evaluator → `requires_approval = True`
- Evaluator's −1 ratio > 2× global average → admin alert

### Support Slot Priority

| Priority | Trigger                                  |
|----------|------------------------------------------|
| P1       | Emergency vacancy, legal compliance risk  |
| P2       | Mandatory 5-day PTO deadline approaching  |
| P3       | Store manager / managing pharmacist leave  |
| P4       | Desired leave, health checkup              |
| P5       | Other PTO                                  |

### Auto-Assignment Scoring

Candidate score (higher = preferred):
- +100: experienced at the target store
- +50: visited within last 3 months
- +min(margin×2, 20): HR headroom above required difficulty
- Prerequisites: HR ≥ required, no conflicts, solo-capable if needed

### Effective Difficulty (per support slot, in HR units)

```
effective_difficulty_hr =
    base_difficulty × 10
    − (5 if chief present)
    − (attending_pharmacists × 3)
    + (solo_hours × 2)
    + forecast_penalty  # A=+10, B=+5, C=0, D=−5, E=−10
```

## API Endpoints

```
POST   /api/auth/token/                    # Obtain JWT
POST   /api/auth/token/refresh/            # Refresh JWT

GET|POST        /api/accounts/users/        # User CRUD (admin)
GET             /api/accounts/users/me/     # Current user profile
POST            /api/accounts/users/change_password/

GET|POST        /api/stores/                # Store CRUD
GET|PUT|DELETE  /api/stores/{id}/

GET|POST        /api/staff/members/         # Staff CRUD
GET|POST        /api/staff/rounders/        # Rounder CRUD
GET|POST        /api/staff/experience/      # Store experience CRUD

GET|POST        /api/shifts/periods/        # Shift period CRUD
GET|POST        /api/shifts/entries/        # Shift CRUD
POST            /api/shifts/entries/load_rates/  # Load rate calc

GET|POST        /api/assignments/slots/     # Support slot CRUD
POST            /api/assignments/slots/{id}/generate_candidates/
GET|POST        /api/assignments/entries/   # Assignment CRUD
POST            /api/assignments/entries/{id}/confirm/
POST            /api/assignments/entries/{id}/reject/

GET|POST        /api/hr/evaluations/        # HR eval (create + list only)
POST            /api/hr/evaluations/{id}/add_comment/
GET             /api/hr/evaluations/bias_check/?evaluator_id=
GET             /api/hr/summaries/          # HR period summaries
POST            /api/hr/summaries/recalculate/

GET|POST        /api/leave/requests/        # Leave request CRUD
POST            /api/leave/requests/{id}/review/
GET             /api/leave/requests/paid_leave_alerts/

GET|POST        /api/analytics/records/     # Prescription records
POST            /api/analytics/records/upload_csv/
GET             /api/analytics/forecasts/   # Prescription forecasts

GET             /api/notifications/logs/    # Notification logs
POST            /api/notifications/logs/send/  # Manual notification
```

## Database Tables

| Table                      | App           | Notes                   |
|----------------------------|---------------|-------------------------|
| users                      | accounts      | Custom email-based user |
| audit_logs                 | accounts      | INSERT-only             |
| stores                     | stores        |                         |
| staff                      | staff         |                         |
| rounders                   | staff         |                         |
| rounder_store_experience   | staff         |                         |
| shift_periods              | shifts        |                         |
| shifts                     | shifts        | Unique(staff,date,type) |
| support_slots              | assignments   |                         |
| assignments                | assignments   |                         |
| hr_evaluations             | hr_system     | INSERT-only             |
| hr_period_summaries        | hr_system     |                         |
| leave_requests             | leave         |                         |
| prescription_records       | analytics     | Unique(store,date)      |
| prescription_forecasts     | analytics     | Unique(store,date)      |
| notification_logs          | notifications | INSERT-only             |

## Environment Variables

```
DJANGO_SECRET_KEY        # Required in production
DJANGO_DEBUG             # "True" or "False"
DJANGO_ALLOWED_HOSTS     # Comma-separated hostnames
DATABASE_URL             # PostgreSQL connection string
REDIS_URL                # Redis for Celery broker
CORS_ALLOWED_ORIGINS     # Frontend origin(s)
ZOOM_ACCOUNT_ID          # Zoom Server-to-Server OAuth
ZOOM_CLIENT_ID
ZOOM_CLIENT_SECRET
```

## Testing

30 unit tests covering:
- User model role checks, audit log immutability
- Store effective difficulty calculation
- Rounder initial HR calculation
- Shift double-booking prevention
- Managing pharmacist store restriction
- HR growth curve (low/mid/high range)
- HR evaluation INSERT-only enforcement
- Support slot difficulty calculation
- Assignment scoring and prerequisite checks

Run: `python manage.py test apps`

## Conventions

- **Language in code**: Model verbose names and user-facing strings are in Japanese; code identifiers, comments, and documentation are in English
- **Settings**: `config/settings.py` — single settings file (no split by env)
- **Working directory**: All Django commands from `backend/`
- **Business logic**: Complex logic in `services.py`, validation in `validators.py`, models stay lean
- **Permissions**: Always use permission classes from `apps/accounts/permissions.py`
