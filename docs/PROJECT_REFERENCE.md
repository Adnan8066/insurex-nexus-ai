# InsureX Nexus AI: Complete Project Reference

A detailed, code-derived reference for the whole repository: architecture, every backend app (models, endpoints, business rules), the ML and RL layers, the React frontend (routes, pages, services), configuration, testing, deployment, and known issues.

> **Demonstration platform.** Premium rates, depreciation factors and policy tiers are illustrative. The RL routing data is synthetic. Fraud scores rank claims for review and are not proof of fraud. Every AI output is advisory and needs a human decision.

---

## Table of contents

1. [What the system does](#1-what-the-system-does)
2. [Architecture and tech stack](#2-architecture-and-tech-stack)
3. [Repository layout](#3-repository-layout)
4. [User roles and access model](#4-user-roles-and-access-model)
5. [End-to-end business workflow](#5-end-to-end-business-workflow)
6. [Backend: configuration and shared code](#6-backend-configuration-and-shared-code)
7. [Backend: apps in detail](#7-backend-apps-in-detail)
8. [Machine learning (tabular models)](#8-machine-learning-tabular-models)
9. [RL claim-routing advisory](#9-rl-claim-routing-advisory)
10. [AI API wiring (`/api/v1/ai/`)](#10-ai-api-wiring-apiv1ai)
11. [Frontend](#11-frontend)
12. [Configuration reference](#12-configuration-reference)
13. [Testing](#13-testing)
14. [Deployment and CI](#14-deployment-and-ci)
15. [Known issues and inconsistencies](#15-known-issues-and-inconsistencies)

---

## 1. What the system does

InsureX Nexus AI is an AI-assisted **motor insurance** platform aimed at the Indian market (INR, +91 phones, km odometers, state codes like MH/KA). It covers the full policy-to-claim lifecycle:

| Area | Capability |
|---|---|
| Policies | Quote → bind → active policy, premium instalments, endorsements (mid-term changes) with approval |
| Vehicles | Insured vehicle records with VIN validation, documents and service history |
| Claims (FNOL) | 4-step claim wizard, document uploads, status workflow, timeline, notes, tracking |
| AI assessment | Repair-cost regression, fraud-risk classifiers, total-loss classifier |
| Fraud / SIU | Fraud alerts, investigations, evidence, interview notes |
| Decision center | Rule-based multi-"agent" pipeline that always ends in human review |
| Routing advisory | PPO reinforcement-learning model recommending which adjuster should take a claim (advisory only) |
| Analytics | Role-aware dashboards, trends, fraud distribution |
| Notifications | In-app notifications with unread badge and preferences |

---

## 2. Architecture and tech stack

```
┌────────────────────┐   HTTPS + JWT    ┌──────────────────────────────┐
│  React 18 SPA      │ ───────────────▶ │ Django 5 + DRF  (/api/v1/)   │
│  Vite, Tailwind    │ ◀─────────────── │  apps/*  common/*  config/   │
│  (Vercel)          │   JSON envelope  │  (Render, gunicorn)          │
└────────────────────┘                  └──────┬───────────┬───────────┘
                                               │           │
                                   ┌───────────▼──┐   ┌────▼───────────────┐
                                   │ PostgreSQL / │   │ ML artifacts        │
                                   │ SQLite (dev) │   │ backend/ml/models   │
                                   └──────────────┘   │ backend/rl/models   │
                                                      └─────────────────────┘
```

| Layer | Technology |
|---|---|
| Frontend | React 18.3, react-router-dom 6.30, Vite 5.4, Tailwind 3.4, axios, Chart.js 4 + react-chartjs-2, lucide-react icons, date-fns, clsx. No TypeScript, no frontend tests. |
| Backend | Django 5.0.6, DRF 3.15.2, simplejwt 5.3.1 (with token blacklist), django-filter, django-cors-headers, drf-spectacular (OpenAPI), WhiteNoise, gunicorn |
| Database | SQLite by default; PostgreSQL via `DATABASE_URL` or `POSTGRES_*` |
| Tabular ML | scikit-learn RandomForest, LightGBM, `CalibratedClassifierCV`, joblib |
| RL | Gymnasium 1.4.0, Stable-Baselines3 2.9.0 (PPO), PyTorch |
| Installed but unused | Celery + Redis (no tasks), MLflow URI setting |
| CI/CD | Jenkins (Windows `bat` steps), Render Blueprint, Vercel |

---

## 3. Repository layout

```
.
├── frontend/                     React + Vite client
│   ├── src/
│   │   ├── main.jsx, App.jsx, index.css (~1080 lines of design tokens/classes)
│   │   ├── routes/AppRoutes.jsx  all routes + guards
│   │   ├── context/              AuthProvider, useAuth
│   │   ├── services/             one axios service per backend area
│   │   ├── pages/                auth, dashboard, admin, claims, policies, vehicles,
│   │   │                         ai, fraud, investigator, decision, operations,
│   │   │                         notifications, support, profile, settings
│   │   ├── components/           layout, ui, charts, tables, forms, auth
│   │   ├── constants/domain.js   mirrors Django choice values
│   │   ├── data/policyTiers.js   8 illustrative Indian motor tiers
│   │   └── utils/                helpers.js, claimPermissions.js
│   ├── vercel.json               SPA rewrite
│   └── .env.example              VITE_API_BASE_URL
├── backend/
│   ├── django_backend/
│   │   ├── config/               settings, urls, wsgi/asgi
│   │   ├── common/               permissions, exceptions, middleware, risk, uploads, params, pagination
│   │   ├── apps/                 accounts, customers, policies, vehicles, claims, assessments,
│   │   │                         investigations, notifications, analytics, settlements*, repair_shops*
│   │   ├── ml_service.py         tabular model loading + inference
│   │   └── media/                uploaded files (git-ignored)
│   ├── data/                     insurance_claims.csv (1,000 rows), fraud_oracle.csv (15,420 rows), demo/
│   ├── ml/models/                trained artifacts + training_report.json
│   └── rl/                       routing env, dataset gen, training, evaluation, recommender, tests
├── docs/                         PROJECT_REFERENCE.md, WORKFLOW.md, DATASETS.md, DEPLOYMENT.md
├── render.yaml                   Render Blueprint
└── Jenkinsfile                   CI pipeline
```

\* `settlements` exists but is not installed; `repair_shops` is retired (migrations only). See §15.

---

## 4. User roles and access model

Four roles (`accounts.Role`): **customer**, **employee** ("Insurance Employee"), **investigator**, **admin**. Public sign-up always creates a customer; admins create staff via `/auth/users/` (admins cannot create other admins there).

### Permission classes (`common/permissions.py`)

| Class | Allows |
|---|---|
| `IsStaffMember` | employee, investigator, admin |
| `IsEmployee` | employee, admin |
| `CanIssuePolicy` | customer, employee, admin (excludes investigator) |
| `IsAdmin` | admin |
| `IsOwnerOrAdmin` | admin/staff, or the object's user/customer |

### Data scoping (applied to querysets)

| Role | Sees |
|---|---|
| admin, employee | everything |
| investigator | only claims where `assigned_investigator` = self, plus the related customers, policies, vehicles, investigations |
| customer | only own records; model outputs (`ai_assessment`, `fraud_risk_score`, `total_loss_probability`) and internal notes are stripped from responses |

### Frontend visibility (Navbar)

Related pages are grouped into dropdowns; a group with one visible page shows as a plain link.

| Menu | Pages | Roles |
|---|---|---|
| Dashboard | role-based dashboard | all |
| Claims | claim list, details, tracking | all |
| Policies ▾ | Policies, Vehicles | customer, employee, admin |
| Fraud ▾ | Fraud alerts (`/fraud`), Investigation cases (`/investigators`, employee/admin only) | employee, investigator, admin |
| AI Tools ▾ | Claim assessment (`/ai-assessment`), Automated review (`/ai-decision`) | employee, investigator, admin |
| Analytics | `/analytics` | employee, investigator |
| Help & Support | `/support` | customer |
| User menu → Administration | User management (admin), Model health (`/operations`, staff) | |

Routing advice (`/routing-advisory`) is not listed in the navigation while its model fails the evaluation gate; the route still works.

---

## 5. End-to-end business workflow

```
Customer registers ─▶ Vehicle added ─▶ Staff quotes policy ─▶ Bind quote ─▶ ACTIVE policy
                                                                              │
     ┌────────────────────────────────────────────────────────────────────────┘
     ▼
FNOL: claim submitted (complexity score computed, notification, optional auto-assign)
     │
     ├─▶ AI assessment (repair cost, fraud score, total-loss probability, priority)
     ├─▶ Routing advice (PPO, advisory) ─▶ human accepts/rejects ─▶ manual assignment
     │
     ▼
submitted → under_review → ai_assessment → investigation → approved / rejected
                                               │                │
                                  FraudAlert + Investigation    ▼
                                  (must be completed before   repair_settlement → closed
                                   approving a high-risk claim)
```

### Claim status rules (`claims/workflow.py check_transition`)
- Only **employee/admin** may set `approved` or `rejected` (else 403).
- Cannot approve from `submitted` or `investigation` (409).
- A **high-risk** claim (`fraud_risk_score > 65`) needs an Investigation with status `completed` or `closed` before approval (409).
- Closing sets `closed_at`. Every change writes `ClaimStatusHistory` + `ClaimTimeline` and notifies the customer.

---

## 6. Backend: configuration and shared code

### `config/urls.py`

| Path | Target |
|---|---|
| `/` | redirect to Swagger UI |
| `/api/health/` | `{"status":"ok"}` (no auth) |
| `/admin/` | Django admin |
| `/api/v1/schema/`, `/swagger-ui/`, `/redoc/` | OpenAPI |
| `/api/v1/auth/` | accounts |
| `/api/v1/customers/` | customers |
| `/api/v1/policies/` | policies |
| `/api/v1/vehicles/` | vehicles |
| `/api/v1/claims/` | claims |
| `/api/v1/assessments/` | assessments router |
| `/api/v1/ai/` | `assessments/ai_urls.py` (ML, vision, RL) |
| `/api/v1/investigations/` | investigations |
| `/api/v1/notifications/` | notifications |
| `/api/v1/analytics/` | analytics |

### REST framework settings
- Auth: `JWTAuthentication` only; default permission `IsAuthenticated`.
- Filters: DjangoFilterBackend, SearchFilter, OrderingFilter.
- Pagination: `PageNumberPagination`, page size 20.
- Throttles (scoped): login 10/min, password_reset 5/hour, register 20/hour, public_form 20/hour.
- JWT: access 60 min, refresh 7 days, rotation + blacklist after rotation, HS256, `Authorization: Bearer`.

### Shared modules (`common/`)
- **`exceptions.py`**: every error becomes `{success:false, error:{code, message, details, request_id}, detail}`; unhandled errors → 500 with a generic message in production.
- **`middleware.py`**: `RequestIDMiddleware` accepts a safe incoming `X-Request-ID` or generates one, echoes it in the response and logs.
- **`risk.py`**: fraud bands, low < 30, medium 30–65, high > 65.
- **`uploads.py`**: max 25 MB, extension allow-lists (images; documents = images + PDF; evidence = documents + mp4/mov/m4a/mp3/wav), **magic-byte check**, PIL verify for images, stored as random `uuid4` filenames.
- **`params.py`**: `parse_int` → 400 on bad query params; `Conflict` → 409.

### Security defaults (production, `DEBUG=False`)
SSL redirect, HSTS 1 year (+subdomains, preload), secure cookies, `X_FRAME_OPTIONS=DENY`, nosniff, referrer `same-origin`, WhiteNoise static files, `SECRET_KEY` required.

---

## 7. Backend: apps in detail

### 7.1 accounts: `/api/v1/auth/`

**Models**
- `User` (extends AbstractUser, table `users`): `email` (login field, unique), `role`, `phone`, `address`, `department`, `avatar`, `is_verified`, `last_login_ip`, `password_reset_token`, `password_reset_token_created`.
- `UserProfile`: bio, date_of_birth, emergency contact, preferred_language, timezone, notification_email/sms/push flags.

**Endpoints**

| Method | Path | Notes |
|---|---|---|
| POST | `register/` | Always creates a customer; username derived from email; returns tokens + user |
| POST | `login/` | email + password; records last login IP |
| POST | `logout/` | blacklists refresh token |
| POST | `refresh/` | new access token (no rotation) |
| POST | `token/refresh/` | simplejwt refresh **with rotation** (used by frontend) |
| GET | `me/`, `profile/` | current user |
| PATCH | `profile/`, `update_profile/` | update with nested profile |
| GET/POST | `users/` | admin: list/create customer, employee, investigator |
| GET | `support-contacts/` | active admins/employees (excludes demo/invalid emails) |
| POST | `change-password/` | checks current password |
| POST | `forgot_password/`, `password-reset/` | emails `{FRONTEND_URL}/forgot-password?token=…`; always generic reply |
| POST | `reset_password/`, `password-reset/confirm/` | token valid 1 hour |

### 7.2 customers: `/api/v1/customers/`

**Models**: `Customer` (`CUST-XXXXXXXX`, license info, credit_score, risk_rating, notes), `CustomerDocument` (id/license/insurance/registration/other), `CallbackRequest` (name, phone, vehicle_type car/two_wheeler/commercial/other, consent, status new/contacted/closed).

**Endpoints**
- `callback-requests/`: POST is **public** (throttled, phone 7–15 digits, consent required); list/patch for staff.
- `/`, `/{id}/`: CRUD; duplicate profile → 409; customers cannot set credit_score/risk_rating/notes.
- `/{id}/documents/` GET/POST; `/me/`.

### 7.3 policies: `/api/v1/policies/`

**Models**
- `Policy` (`POL-XXXXXXXX`): customer, agent, `type` (auto_comprehensive, auto_collision, auto_liability, homeowners, renters, umbrella), `status` (active, expired, cancelled, pending, suspended), start/end dates, premium, deductible, payment_frequency (monthly/quarterly/semi_annual/annual), auto_renew, `coverage` JSON, vehicle, property fields. Properties `is_active`, `days_remaining`.
- `PolicyApplication`: the quote. Status quoted/bound/declined, applicant/asset/risk JSON, asset_value, coverage_limit, deductible, risk_score, quoted_premium, rating_breakdown, policy_terms, bound_policy.
- `PolicyEndorsement`: change request. Status pending/approved/rejected, proposed_changes, premium_delta, before/after snapshots, reviewer.
- `PolicyCoverage`, `PolicyDocument`, `PremiumHistory` (pending/paid/overdue/cancelled).

**Premium formula** (`services/rating.py`)
```
base              = coverage_limit × 0.025              (POLICY_BASE_ANNUAL_RATE)
risk_loading      = base × risk_score / 100
deductible_ratio  = min(deductible / coverage_limit, 1)
deductible_credit = (base + risk_loading) × deductible_ratio × 0.20   (POLICY_DEDUCTIBLE_CREDIT_RATE)
premium           = max(0.01, base + risk_loading − deductible_credit)   rounded half-up
```
Example: coverage ₹10,00,000, deductible ₹50,000, risk 40 → base 25,000 + loading 10,000 − credit 350 = **₹34,650.00**.

**Endpoints**

| Method | Path | Permission | Behaviour |
|---|---|---|---|
| GET | `/`, `/{id}/` | auth | lookup by id or policy_number |
| POST | `/` | employee | create; links vehicle; notification |
| PUT/PATCH/DELETE | `/{id}/` | admin | syncs vehicle links; activation → high-priority notification |
| POST | `quote/` | auth | creates PolicyApplication + rating breakdown |
| POST | `bind-quote/` | employee | `{application_id}` → active Policy, first PremiumHistory instalment (premium ÷ 12/4/2/1), notification |
| GET/POST | `/{id}/endorsements/` | employee | create pending endorsement (premium + delta must stay > 0) |
| POST | `/{id}/endorsements/{eid}/approve/` | employee | merges coverage, appends `assets_add` to `coverage.scheduled_assets`, updates deductible/premium, pending billing row |
| POST | `/{id}/endorsements/{eid}/reject/` | employee | |
| GET | `form-options/` | employee | customers, agents, investigators, unlinked vehicles, policies |
| GET/POST | `/{id}/documents/` | auth / admin | |
| GET/POST | `/{id}/premium-history/` | auth / admin | see §15 route collision |
| GET/PUT/PATCH | `/{id}/coverage/` | auth / admin | see §15 route collision |
| GET | `expiring/?days=30` | auth | active policies ending soon |

### 7.4 vehicles: `/api/v1/vehicles/`

**Models**: `Vehicle` (make, model, year, **VIN** 17 chars unique, color, license_plate, license_state, registration_expiry, purchase date/price, mileage, fuel_type gasoline/diesel/hybrid/electric/plugin_hybrid, transmission automatic/manual/cvt/semi_automatic, status active/sold/total_loss/salvage/inactive, engine_size, body_style, features), `VehicleDocument`, `VehicleHistory`.

**Rules**: VIN regex `^[A-HJ-NPR-Z0-9]{17}$` (no I/O/Q), not editable after creation; year 1900…next year; a vehicle with claims cannot be deleted (409); policy must belong to the same customer and not be linked elsewhere.

**Endpoints**: CRUD (`CanIssuePolicy` for writes), `/{id}/claims/`, `/{id}/documents/`, `/{id}/history/`, `registration-expiring/?days=30`.

### 7.5 claims: `/api/v1/claims/`

**Models**
- `Claim` (`CLM-XXXXXXXX`): customer, policy, vehicle, incident date/time, `incident_type` (collision, comprehensive, theft, vandalism, fire, water_damage, hail, animal, glass, other), `incident_severity` (minor, moderate, major, total_loss), location + lat/long, number_of_vehicles, injuries/property_damage/witnesses/police_report (+ details), claim_amount, estimated_repair_cost, complexity_score, description, `status` (8 values), `priority` (low/medium/high/critical), assigned_adjuster, assigned_investigator, ai_assessment JSON, fraud_risk_score, total_loss_probability, timestamps.
- `ClaimDocument` (police_report, photos, medical, estimate, invoice, receipt, total_loss, settlement, weather, correspondence, other; verification fields), `ClaimStatusHistory`, `ClaimTimeline`, `ClaimNote` (internal by default).

**Complexity score (on creation)**
```
complexity = min(1, 0.2 + 0.12·min(max(vehicles−1,0),3) + 0.2·injuries
                    + 0.12·property_damage + 0.08·witnesses + 0.08·police_report)
```

**Validation**: policy/vehicle must belong to the same customer and match each other; incident date inside the policy term and not in the future; claim_amount > 0.

**Endpoints**

| Method | Path | Permission | Behaviour |
|---|---|---|---|
| GET/POST | `/` | CanIssuePolicy for POST | create → history, timeline, notification, `auto_assign_new_claim` (fail-safe) |
| GET/PUT/PATCH/DELETE | `/{id}/` | scoped | customers edit/delete only while `submitted`; status cannot be changed here |
| GET/POST | `/{id}/documents/` | scoped | validated upload |
| POST/PATCH | `/{id}/update-status/` | employee | workflow rules (§5) |
| GET/PATCH | `/{id}/status/` | | |
| POST | `/{id}/assign-adjuster/` | employee | employee/admin only |
| POST | `/{id}/assign-investigator/` | employee | sets status `investigation`, upserts **FraudAlert**, creates **Investigation** (`INV-XXXXXXXX`) |
| GET/POST | `/{id}/notes/` | scoped | customers see/write only non-internal notes |
| GET | `/{id}/timeline/` | scoped | |
| POST | `/{id}/assessment/` | staff | runs all 3 models, writes scores onto the claim |
| GET | `my-claims/`, `assigned-to-me/` | | paginated |

**Management commands**
- `import_project_datasets [--dry-run --skip-insurance --skip-fraud]`: idempotent import of both CSVs into User/Customer/Policy (expired)/Vehicle (synthetic VIN)/Claim (`INS-…`, `FO-…`). Fraud rows → status `investigation`, score 85; others → `closed`, score 10. The raw row is kept in `ai_assessment.source_data`.
- `train_project_models`: trains all tabular models (§8).

### 7.6 assessments: `/api/v1/assessments/` (+ `/api/v1/ai/`)

**Models**
- `ClaimAssessment` (1:1 claim): type, status (pending/in_progress/completed/failed/requires_review), predicted_repair_cost, cost_breakdown, repair_time_estimate_days, fraud_risk_score, risk_level, risk_factors, behavioral_indicators, network_analysis, total_loss_probability, claim_priority, ai_recommendation, confidence, reviewer.
- `AgentOutput` (claim × agent_type unique): claim/policy/fraud/damage/decision agent outputs, timings, errors.
- `DecisionFlow` (1:1 claim): agents history, rl_recommendation, final_decision.
- `ModelPerformance`: metrics registry (accuracy, precision, recall, F1, MAE, RMSE, R², AUC…).
- `RoutingAgentProfile` (1:1 user): skill_tier 1–5, is_available, is_demo.
- `RoutingRecommendationReview`: recommendation_id, claim, reviewer, decision accepted/rejected, notes, snapshots.

**Router endpoints (staff)**: `assessments/` (+ `/{id}/review/`, `/{id}/request-review/`), `agent-outputs/`, `decision-flows/`, `model-performance/` (+ `active/`).

**Command** `seed_routing_demo_agents`: 3 demo staff (Aarav Sharma, employee, tier 4; Priya Nair, investigator, tier 5; Rohan Patel, employee, tier 3) with `@example.invalid` emails and unusable passwords.

### 7.7 investigations: `/api/v1/investigations/`

**Models**: `Investigation` (1:1 claim, `INV-XXXXXXXX`, status open/in_progress/pending_review/completed/closed/on_hold, priority, findings, conclusion, recommendation, dates), `InvestigationEvidence` (10 evidence types, file, key-evidence flag, verification), `InvestigationNote` (interview flag, interviewee, confidential), `FraudAlert` (1:1 claim, risk score/level/factors, status new/investigation/reviewed/dismissed/escalated).

**Endpoints (staff only; investigators see their own)**
- `fraud-alerts/`: CRUD + `/{id}/review/`, `/{id}/escalate/` (assigns caller), `/{id}/dismiss/`, `high-risk/`.
- `/`: CRUD + `/{id}/evidence/`, `/{id}/notes/`, `/{id}/start/`, `/{id}/complete/` (a completed investigation unblocks approval of a high-risk claim).

### 7.8 notifications: `/api/v1/notifications/`

- `Notification`: recipient, type (claim, policy, payment, document, ai_assessment, fraud_alert, settlement, system, reminder), priority (low/normal/high/urgent), title, message, link, related object, read state.
- `NotificationPreference`: 15 email/push/SMS toggles (stored but **not read by any sender**).
- `services.create_in_app_notification(...)` creates in-app rows only (no email/push delivery).
- Endpoints: list/retrieve (own), `/{id}/mark-read/`, `mark-all-read/`, `unread-count/`, `by-type/?type=`, `preferences/` GET/PUT/PATCH.

### 7.9 analytics: `/api/v1/analytics/`

- Models: `DashboardMetric`, `AnalyticsSnapshot`, `Report`, `ReportExecution`.
- `GET dashboard/?timeframe=week|month|quarter|ytd|year`: claims (total, by status, by type, amounts, total-loss vs repairable at ≥ 50%), policies (total, active, expiring in 30 days), fraud (high-risk > 65, flag rate, SIU referrals), customer/vehicle totals. Customers get their own data with fraud/portfolio blocks removed.
- `GET fraud-risk/` (staff): band counts + thresholds.
- `GET claims-trend/?timeframe=|days=&granularity=day|month`: zero-filled buckets.
- `reports/` + `/{id}/run/` (claims_summary, financial_summary, fraud_analysis, performance), `executions/`, `metrics/`, `snapshots/latest/`.
- `POST export/` → 501 (not configured). `GET overview/` → see §15.

### 7.10 settlements (present but **not installed or routed**)

- `Settlement` (`SET-XXXXXXXX`), `SettlementTimeline`, `SettlementPayment` (`PAY-XXXXXXXX`).
- **Payout formula** (`services/payout.py`):
```
depreciation_rate = min(0.05 × vehicle_age_years, 0.80)
depreciation      = 0 if zero-depreciation add-on else repair_cost × depreciation_rate
payout            = max(0, repair_cost − deductible − depreciation)
```
- Designed flow: create (claim must be approved) → approve (moves the claim to `repair_settlement`) / reject → pay → complete-payment.

### 7.11 repair_shops (retired)
Only migrations remain (0001 creates RepairShop/RepairJob/…; 0002 deletes them) plus `tests.py` with smoke tests (health + 401 on core endpoints).

---

## 8. Machine learning (tabular models)

### Datasets

| File | Rows | Target(s) | Notes |
|---|---|---|---|
| `insurance_claims.csv` | 1,000 | `fraud_reported` (Y 247 / N 753), `vehicle_claim`, `incident_severity` | severity: Minor 354, Total Loss 280, Major 276, Trivial 90 |
| `fraud_oracle.csv` | 15,420 | `FraudFound_P` (923 fraud, 6.0%, 15.7:1 imbalance) | no missing values or duplicates; `PolicyNumber`/`RepNumber` excluded as IDs |

Strongest fraud associations in Fraud Oracle (Cramér's V): PolicyType 0.168, BasePolicy 0.162, VehicleCategory 0.137, Fault 0.131.

### Training pipeline (`python manage.py train_project_models`)

The current artifacts come from this command, trained from `backend/data/`.

**Preprocessing** (inside each saved pipeline): numeric → median impute + StandardScaler; categorical → most-frequent impute + OneHotEncoder(ignore unknown).

**Insurance features (13)**: age, policy_deductable, policy_annual_premium, number_of_vehicles_involved, bodily_injuries, witnesses, auto_year, incident_type, incident_severity, property_damage, police_report_available, auto_make, auto_model.

| Artifact | Algorithm | Target |
|---|---|---|
| `fraud_risk.joblib` | RandomForestClassifier (250 trees, depth 12, min_leaf 4, balanced_subsample) | `fraud_reported == Y` |
| `repair_cost.joblib` | RandomForestRegressor (same params) | `vehicle_claim` |
| `total_loss.joblib` | RandomForestClassifier, without `incident_severity` (to avoid leakage) | `incident_severity == "Total Loss"` (proxy label) |
| `fraud_oracle_fraud.joblib` | LightGBM (350 trees, 15 leaves, lr 0.03, scale_pos_weight 3) wrapped in sigmoid `CalibratedClassifierCV(cv=3)`, 30 features | `FraudFound_P == 1` |

**Fraud Oracle evaluation protocol**: 80/20 dev/test → dev split 75/25 train/validation → threshold sweep 0.05–0.50 on validation (requires recall ≥ 0.75 and precision > base rate; choose best precision) → single test evaluation → refit on all rows. Writes `fraud_oracle_evaluation.png` (PR, ROC, confusion matrices).

### Metrics (`training_report.json`, trained 2026-10-14)

| Model | Metrics |
|---|---|
| insurance_fraud (thr 0.5) | Accuracy 0.83, Precision 0.632, Recall 0.735, F1 0.679, ROC-AUC 0.765 |
| repair_cost | MAE 7,733, RMSE 10,627, R² 0.67 |
| total_loss (thr 0.5) | Accuracy 0.65, Precision 0.403, Recall 0.518, F1 0.453, ROC-AUC 0.686 |
| fraud_oracle_fraud (thr 0.10, 3,084 test rows) | Precision 0.164, **Recall 0.773**, F1 0.271, ROC-AUC 0.848, PR-AUC 0.247, alert rate 28.3%; TN 2170 / FP 729 / FN 42 / TP 143 |
| previous RF at thr 0.803 (for comparison) | Recall 0.005 (caught 1 of 185 frauds) |

### Inference (`ml_service.py`)
- Lazy loading with reload on file change; `n_jobs` forced to 1.
- `claim_model_input(claim)`: imported claims use their original CSV row; live claims are mapped to the insurance schema (collision → Single/Multi-vehicle Collision, theft → Vehicle Theft, comprehensive → Parked Car; minor/moderate → Minor Damage, major → Major Damage, total_loss → Total Loss; age from DOB).
- `detect_fraud_ml`: Fraud Oracle model for `fraud_oracle` rows, otherwise `fraud_risk`. Score = P × 100; high ≥ 65 (`FRAUD_HIGH_THRESHOLD`; Oracle: ≥ 10); medium ≥ min(40, thr/2).
- `predict_repair_cost_ml` → `{cost}`; `predict_total_loss_ml` → `{probability}` (both unavailable for Fraud Oracle rows).
- `MLModelUnavailable` → HTTP 503.

### Where scores are written (`apps/assessments/ai_views.run_claim_assessment`)
- Runs all three models, fills the `ClaimAssessment` row, and copies `fraud_risk_score`, `total_loss_probability` and a `fraud_risk` block onto the claim (merged into `ai_assessment`, so imported claims keep their `source_data`).
- Raises or refreshes the claim's `FraudAlert` when the score is in the moderate band (≥ 30) or above; an existing alert keeps its status, investigator and notes.
- Called by `POST /ai/assess-claim/`, `POST /claims/{id}/assessment/`, automatically when a claim is submitted (failures are logged and never block the claim), and by `python manage.py assess_claims` for backfills.

---

## 9. RL claim-routing advisory

### Environment (`rl/environment.py`, `ClaimRoutingEnv`)
- **Agents**: 3–5 adjusters; max queue 20, max workload 100, skill tiers 1–5.
- **Observation** (23 floats in [0,1]): `[complexity, severity, difficulty]` + per agent `[queue/20, workload/100, skill_ok, available]` × 5.
- **Action**: index of the agent to assign.
- **Dynamics**: `claim_workload = 1 + 4·complexity + 5·difficulty`; each step every agent's workload −4 and queue −1; the chosen agent gets +workload and +1 queue.
- **Reward**:
```
reward = 1.0 − 10·(wait/55) − 2·(std(workloads)/100) − (8 if required_tier > agent_tier else 0)
wait   = queue·1.5 + workload/4
```
- Episode = 100 steps.

### Data and training
- `generate_dataset.py`: synthetic transitions (200 episodes × 100 steps = 20,000 rows) from `random`, `least_workload` or `mixed` behaviour policies.
- `training.py`: PPO (`MlpPolicy`, lr 3e-4, n_steps 256, batch 64, γ 0.99), warm-started by **behaviour cloning** on expert (`least_workload`) transitions (100 epochs), then 50,000 PPO timesteps.
- **Evaluation gate**: PPO must be at least as good as the least-workload heuristic on reward, wait, workload std and skill-mismatch rate across many seeds. Report → `<model>.evaluation.json`.

### Current results (both gates **failed**)

| Run | Policy | Reward | Wait | Workload std | Mismatch |
|---|---|---|---|---|---|
| `claim_routing_ppo` (50k steps, 10 seeds) | least_workload | −0.77 | 0.56 | 2.53 | 0.214 |
| | PPO | −1.59 | 6.72 | 10.96 | 0.281 |
| `claim_routing_candidate` (250k steps, 50 seeds) | least_workload | 0.43 | 0.28 | 2.34 | 0.065 |
| | PPO | 0.33 | 2.71 | 5.16 | 0.065 |

The simple heuristic still beats PPO, so production recommendations and auto-assignment stay **disabled** (`CLAIM_ROUTING_ENFORCE_EVALUATION_GATE=True`).

### Recommendation engine (`rl/recommendation.py`)
Encodes the claim and 3–5 agents → PPO deterministic action + action probabilities (renormalised over available agents) → ranked options with match %, predicted wait, skill match, workload before/after. The response always carries `advisory_only: true`, `automated_assignment: false`, `requires_human_review: true`.

### Claim → RL features (`rl_views._claim_routing_features`)
- severity: minor 0.15, moderate 0.4, major 0.7, total_loss 1.0
- complexity: stored `complexity_score`
- difficulty: `0.65·severity + 0.15·injuries + 0.08·property + 0.06·witnesses + 0.06·police`

### Auto-assignment (fail-closed)
`auto_assign_new_claim` only acts if **all** of these hold: auto-assign is enabled, the gate passed, there are 3–5 real (non-demo) available employee profiles, and the recommended agent has a skill match. Today it never fires.

---

## 10. AI API wiring (`/api/v1/ai/`)

All endpoints require a staff member; investigators can only act on their assigned claims.

| Method | Path | What it does |
|---|---|---|
| POST | `assess-claim/` `{claim_id}` | Runs cost + fraud + total-loss → `ClaimAssessment`; priority critical (fraud > 65), high (fraud > 40 or TL > 50), medium (fraud > 20 or TL > 25), else low; rule-based recommendation (SIU / adjuster review / standard) |
| POST | `predict-repair-cost/`, `detect-fraud/`, `predict-total-loss/` | single model |
| POST | `run-agent/<type>/` | `claim_agent` summary; `policy_agent` coverage validity + vehicle match; `fraud_agent`; `damage_agent`; `decision_agent` always returns `manual_review` |
| GET | `decision-flow/<claim_id>/` | agent pipeline state |
| GET | `model-status/` | which models loaded + training report |
| GET | `routing-model-status/` | readiness, gate result, dependencies |
| GET | `routing-agents/` | staff roster with live queue/workload |
| GET | `routing-claims/` | up to 100 unassigned open claims + features |
| POST | `route-recommendation/` | PPO advice + `recommendation_id` + signed 24 h `review_token`; nothing persisted |
| POST | `route-recommendation/review/` | records accept/reject feedback; never assigns (409 if already reviewed) |

> The "multi-agent" pipeline is **rule-based Python**, not an LLM or agent framework (there is no agent framework).

---

## 11. Frontend

### Bootstrap
`main.jsx` → `StrictMode` → `BrowserRouter` → `AuthProvider` → `App` (`ToastProvider`) → `AppRoutes`. Every page is lazy-loaded with `React.lazy` + `Suspense`.

### Auth flow
- Tokens in `localStorage` (`access_token`, `refresh_token`, `user`).
- On load: GET `/auth/profile/` validates the session.
- Axios interceptor adds the Bearer token; on 401 it calls `/auth/token/refresh/` once and retries, otherwise logs out → `/login`.
- `formatApiError` turns any backend/network error into readable text.

### Routes

| Path | Page | Guard |
|---|---|---|
| `/` | LandingPage (→ /dashboard if logged in) | public |
| `/login`, `/register`, `/forgot-password` | auth pages | public |
| `/dashboard` | role-based: Customer / Employee / Admin (Analytics) / Investigator | auth |
| `/policies`, `/policies/:id` | PolicyList, PolicyDetails | auth |
| `/policies/new`, `/policies/:id/edit` | PolicyForm | admin |
| `/vehicles`, `/vehicles/:id` | VehicleList, VehicleDetails | auth |
| `/vehicles/new`, `/vehicles/:id/edit` | VehicleForm | customer, employee, admin |
| `/claims`, `/claims/new`, `/claims/:id`, `/claims/:id/tracking` | claim pages | auth |
| `/ai-assessment`, `/routing-advisory`, `/fraud`, `/investigators`, `/analytics`, `/ai-decision`, `/operations` | staff tools | employee, admin, investigator |
| `/admin/users` | UserManagement | admin |
| `/notifications`, `/profile`, `/settings` | | auth |
| `/support` | Support | customer, employee, admin |

### Pages

- **LandingPage**: hero with animated car illustration, benefits, cover items, **request-a-callback** modal (public POST), "Explore policy options" modal with the 8 illustrative tiers, dark-mode toggle.
- **Login / Register / ForgotPassword**: email + password; registration with name, email, phone, password ≥ 8, terms; reset by email token.
- **CustomerDashboard**: KPIs (active policies, under review, approved, all claims), recent claims, active cover, **client-side PDF summary download**, retry/offline handling. Internal statuses are shown as "under review".
- **EmployeeDashboard**: timeframe selector; KPIs (active policies, claims, pending, high fraud, likely total loss); charts (claims over time combo, status doughnut, fraud doughnut); recent claims and fraud alert tables; CSV export.
- **AdminDashboard / Analytics**: 7 KPIs, 5 charts (trend, fraud bands, status distribution, total-loss vs repairable, by incident type), CSV export.
- **UserManagement**: create customer/employee/investigator accounts; list managed accounts.
- **InvestigatorDashboard**: SIU profile banner, KPIs, case docket with search/filters, notes modal (interview/confidential tags, add note).
- **ClaimList**: KPIs, search, filters, sortable table, pagination, delete (admin always; others only while `submitted`).
- **SubmitClaim**: 4-step wizard: (1) policy & vehicle (cascading, active-policy check), (2) incident details, (3) injuries/property/police/witnesses, (4) amount in ₹, description, attachments (≤ 25 MB) and review. Uploads run after creation with `Promise.allSettled`.
- **ClaimDetails**: tabs Overview (assign adjuster/investigator), Incident, AI Risk (staff), Documents (upload + thumbnails), Timeline; status changer for admin/employee; lifecycle sidebar.
- **ClaimTracking**: 5 plain-language steps, "what happens next" guidance per role, status history.
- **PolicyList / PolicyDetails**: filters; details with endorsements (create, admin approve), tier info, financial summary, coverage, vehicle, documents, payment schedule modal, printable certificate.
- **PolicyForm**: tier picker, customer/agent, dates, risk score, vehicle auto-fill → **Calculate Quote** (`/quote/`) → shows breakdown → **Issue Active Policy** (`/bind-quote/`).
- **VehicleList / VehicleForm / VehicleDetails**: VIN validation, server-error field mapping, expired-registration warnings, documents, claims history, quick stats.
- **AIAssessment**: pick a claim, re-run inference, KPI cards (cost vs claimed, fraud band, total-loss, priority), recommendation, charts, contributing factors.
- **RoutingAdvisory**: banners (advisory only, model readiness, gate status); pick a live claim or enter features; sample or live agents; get advice; ranked options table; accept/reject feedback.
- **FraudDashboard**: alert queue with risk/status filters; Examine modal → dismiss / mark reviewed / escalate.
- **AIDecisionCenter**: animated 5-agent pipeline run, agent tiles with input/output JSON, final decision (always human review).
- **AIOperations**: model registry from `model-status`, agent executions, priority mismatches, investigator assignments, metrics table and chart.
- **Notifications, Support, Profile, Settings**: inbox with filters; support contacts; profile and password; notification preferences + model availability (staff).

### Shared components
Navbar (role-filtered menus with dropdown groups, notification bell polling every 30 s, dark mode, user menu), Footer, Button/Badge/StatusBadge, Card, Modal/ConfirmDialog, Toasts, Skeletons, ErrorBoundary, Chart wrappers (Bar, Doughnut, Combo), DataTable with sorting/pagination, form fields, DocumentUpload.

### Styling
Tailwind + a large `index.css` with CSS-variable design tokens (primary #2563eb, accent #00c896, Inter font), class-based dark mode persisted in `localStorage.theme`, INR formatting (`en-IN`).

---

## 12. Configuration reference

### Backend environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DEBUG` | `True` | |
| `SECRET_KEY` | dev key (DEBUG only) | required in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | |
| `DATABASE_URL` | — | overrides everything |
| `DATABASE_ENGINE`, `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | sqlite / insurex / postgres / postgres / localhost / 5432 | |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_URL` | localhost:3000/5173 | |
| `USE_X_FORWARDED_PROTO`, `SECURE_SSL_REDIRECT` | | proxy/TLS |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` / `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | 60 / 7 | |
| `POLICY_BASE_ANNUAL_RATE`, `POLICY_DEDUCTIBLE_CREDIT_RATE`, `POLICY_RATING_VERSION` | 0.025, 0.20, demo-v1 | premium formula |
| `CLAIM_ANNUAL_DEPRECIATION_RATE`, `CLAIM_MAX_DEPRECIATION_RATE` | 0.05, 0.80 | payout formula |
| `CLAIM_ROUTING_MODEL_PATH` | `backend/rl/models/claim_routing_ppo.zip` | |
| `CLAIM_ROUTING_ENFORCE_EVALUATION_GATE` | | block advice if the gate failed |
| `CLAIM_ROUTING_AUTO_ASSIGN_ENABLED` | false | |
| `THROTTLE_*_RATE`, `MAX_UPLOAD_BYTES` | see §6, 25 MB | |
| `EMAIL_*` | console backend | password reset emails |
| `LOG_LEVEL` | INFO | |

### Frontend
`VITE_API_BASE_URL` (default `http://127.0.0.1:8000/api/v1`, normalised to end with `/api/v1`). Dev server on port 3000.

### Local run
```powershell
# Backend
cd backend/django_backend
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py import_project_datasets      # optional demo data
python manage.py seed_routing_demo_agents     # optional
python manage.py runserver                    # http://127.0.0.1:8000/api/v1/schema/swagger-ui/

# Frontend
cd frontend
copy .env.example .env.local
npm install; npm run dev                      # http://localhost:3000
```

---

## 13. Testing

| Suite | Covers |
|---|---|
| `accounts/tests.py` | registration forces customer role, password mismatch, login throttle (429), username collisions, support contacts, logout blacklisting |
| `analytics/tests.py` | risk bands, timeframes, dashboard scoping, zero-filled trends, customer restrictions |
| `claims/tests.py` | workflow transitions, high-risk approval guard, field protection, validation, data-leak prevention, upload validation, request IDs, automatic scoring and fraud alerts on submission |
| `customers/tests.py` | underwriting fields protected, duplicate profile 409, callback throttle |
| `investigations/tests.py` | start/complete, notes/evidence, scoping |
| `policies/tests.py` | bad params 400, shared routes, negative values |
| `vehicles/tests.py` | VIN/numeric validation, delete-with-claims 409 |
| `repair_shops/tests.py` | health check, 401 on core endpoints |
| `assessments/test_rl_advisory.py` | routing auth, schema, advisory-only behaviour, gate enforcement, reviews |
| `rl/tests/` (pytest) | Gymnasium `check_env`, mismatch penalty = 8, workload decay, recommendation ranking |

**Not tested**: settlements, notifications, quote/bind/rating formula, payout formula. No frontend tests.

Commands: `npm run lint && npm run build`; `python manage.py check`; `python manage.py spectacular --validate`; `python manage.py test`; `python -m pytest rl/tests`.

---

## 14. Deployment and CI

- **API on Render** (`render.yaml`): Python 3.12.11, free plan; build = pip install + collectstatic + migrate; start = gunicorn `config.wsgi`; health check `/api/health/`; `DEBUG=False`, SSL redirect, generated `SECRET_KEY`, Postgres `DATABASE_URL` (set manually), CORS to `https://frontend-omega-murex-45.vercel.app`, gate enforced, auto-assign off.
- **Frontend on Vercel**: SPA rewrite to `index.html`; set `VITE_API_BASE_URL`.
- **Jenkins** (Windows agent): Checkout (3 retries) → Frontend (`npm ci`, lint, build) → Backend (venv on Python 3.12, `check`, OpenAPI validate, `test`). RL pytest is not in CI.
- Render's free filesystem is ephemeral, so uploaded media needs persistent storage. ML/RL weights must be present on the server (RL `.zip` files are git-ignored).

---

## 15. Known issues and inconsistencies

**Functional**
1. **Settlements app not wired in**: missing from `INSTALLED_APPS` and `config/urls.py`, so its payout endpoints are unreachable and its tables are never migrated. The claim status `repair_settlement` therefore can only be set manually.
2. **Policy route collisions**: `premium-history` (GET vs POST) and `coverage` (GET vs PUT/PATCH) are separate `@action`s with the same `url_path` (`policies/views.py:362-388`). One method of each pair likely returns 405.
3. **`/analytics/overview/` likely 500s**: it passes a DRF `Request` into another `@api_view` (`analytics/views.py:323`).
4. **RL models fail their evaluation gate**: the heuristic beats PPO, so routing advice returns 503 in production and auto-assign never fires.
5. **RL default training dataset breaks BC**: `training.py` defaults to the `mixed` CSV, but behaviour cloning requires `least_workload` rows. Use the `expert` CSV.
6. **Severity ↔ skill-tier mapping differs** between the environment and the recommender for intermediate severities (0.15/0.4/0.7).
7. **ClaimDetails "Incident narrative"** shows template text, not the customer's `description`.
8. **Unguarded frontend routes**: investigators can open `/claims/new`, `/policies`, `/vehicles` by URL (the backend still enforces permissions).

**Dead / unused code**
- `common/pagination.py` and several permission classes are unused.
- `NotificationPreference` is never consulted; Celery/Redis/MLflow configured but unused.
- Many frontend service functions are unused; `.oxlintrc.json` without oxlint.
- `rl/recommendation.py`: stray `from xml.parsers.expat import model`; unused `strategy` parameter.

**Repository hygiene**
- `jenkins.war`, `__pycache__/*.pyc` files and uploaded media were removed from the repository but remain in git history, so clone size only shrinks if history is rewritten.
