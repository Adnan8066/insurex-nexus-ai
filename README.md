# InsureX Nexus AI

An AI-assisted motor insurance platform covering the policy-to-claim lifecycle: policy quoting and issuance, vehicle records, first notice of loss (FNOL), claim tracking, triage scoring, investigations, settlements, and an advisory reinforcement-learning (RL) claim-routing simulator.

- **Frontend:** React 18 + Vite + Tailwind CSS, tested with Vitest (deployed on Vercel)
- **Backend:** Django 5 + Django REST Framework, JWT auth, OpenAPI docs, Celery + Redis for background jobs (deployed on Render)
- **ML:** scikit-learn / LightGBM tabular models, Stable-Baselines3 PPO for routing advice

> **Demonstration only.** Premium tables follow an IRDAI-style structure, but several figures are placeholders, not approved insurer rates. The Indian training data and the RL routing data are synthetic. The triage priority score ranks claims for review and is never a fraud verdict; only an investigator's recorded outcome is. Every AI output is advisory and needs a human decision.

## Repository layout

```
.
├── frontend/                     React + Vite client
│   ├── public/                   Static assets (logo, icons)
│   └── src/
│       ├── components/           Layout, UI, charts, tables, forms
│       ├── constants/            Domain values mirrored from the API
│       ├── context/              Authentication state
│       ├── data/                 Illustrative policy tiers
│       ├── hooks/                Shared React hooks (e.g. usePolling)
│       ├── layouts/              Page shells
│       ├── pages/                One folder per area (claims, policies, ai, fraud, ...)
│       ├── routes/               Route table and role guards
│       ├── services/             API client, one module per backend area
│       ├── test/                 Vitest setup
│       └── utils/                Formatting and permission helpers
├── backend/
│   ├── django_backend/           Django project
│   │   ├── config/               Settings, URLs, WSGI/ASGI, Celery app
│   │   ├── apps/                 Domain apps (see below)
│   │   ├── common/               Permissions, errors, uploads, risk bands, task helpers
│   │   ├── ml_service.py         Loads trained models and scores claims
│   │   └── manage.py
│   ├── data/                     Datasets
│   │   ├── us/                   Lumora synthetic US book: motorsynth generator + config (output not committed)
│   │   ├── insurance_claims.csv  1,000 claims, original US-dollar layout
│   │   ├── fraud_oracle.csv      15,420 claims, original layout
│   │   └── demo/                 Anonymized demo vehicle/policy CSVs
│   ├── ml/models/                Trained model artifacts (created by the training commands)
│   ├── rl/                       Claim-routing RL simulator, training, evaluation
│   └── requirements.txt          Points to django_backend/requirements.txt
├── docs/
│   ├── PROJECT_REFERENCE.md      Full code-level reference
│   ├── WORKFLOW.md               Policy → quote → claim workflow and endpoints
│   ├── DATASETS.md               Dataset import and model training
│   ├── DEPLOYMENT.md             Render + Vercel deployment
│   ├── TRIAGE_SCORE_ROLLOUT.md   What the triage priority score means, and the field rename plan
│   └── *.docx, *.pdf             Plain-English overviews of the platform, data and models
├── ml-learning/                  Self-study notebooks (Python, NumPy, pandas, probability); not used by the app
├── render.yaml                   Render Blueprint for the API
└── Jenkinsfile                   CI: frontend lint/build, backend tests, RL tests, model training
```

### Backend apps

| App | Responsibility |
| --- | --- |
| `accounts` | Custom user model, JWT auth, roles |
| `customers` | Customer profiles, callback requests |
| `policies` | Policy applications, IRDAI-style quotes, binding, premium history, endorsements, expiry and renewal-reminder jobs |
| `vehicles` | Insured vehicle records, including engine capacity and ex-showroom price used for rating |
| `claims` | FNOL, claim lifecycle, dataset import, model training and demo commands |
| `assessments` | AI assessment, triage priority score, background claim scoring, RL routing advisory, workforce endpoints |
| `investigations` | Fraud alerts, investigation cases, investigator outcomes (`confirmed_fraud`, `cleared`, `inconclusive`, `pending`) |
| `settlements` | Payout calculation with depreciation |
| `auditlog` | Audit history for policy, claim, investigation and settlement changes |
| `notifications` | In-app notifications |
| `analytics` | Dashboard metrics |
| `repair_shops` | No live features; kept only so its old migrations still apply |

User roles: `customer`, `employee`, `investigator`, `admin`. Each role gets its own dashboard in the frontend.

## Prerequisites

- Python 3.12 (the version used by CI and Render)
- Node.js 18+ and npm
- Optional: PostgreSQL. SQLite is used by default for local development.
- Optional: Redis, for the Celery worker. Without it, claims are scored inside the request and the scheduled jobs don't run (see [Background jobs](#background-jobs)).

## Quick start (local development)

### 1. Backend API

```powershell
cd backend/django_backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
```

`.env.example` holds **production-style** values. For local development, edit `.env` before going on:

- set `DEBUG=True`
- delete the `DATABASE_URL` line (SQLite is used when it is unset)
- set `ALLOWED_HOSTS=localhost,127.0.0.1`, and `CORS_ALLOWED_ORIGINS` and `FRONTEND_URL` to `http://localhost:3000`

Then:

```powershell
python manage.py migrate
python manage.py createsuperuser  # optional, for /admin and staff access
python manage.py runserver
```

The API runs at <http://127.0.0.1:8000>:

- Swagger UI: <http://127.0.0.1:8000/api/v1/schema/swagger-ui/>
- ReDoc: <http://127.0.0.1:8000/api/v1/schema/redoc/>
- Health check: <http://127.0.0.1:8000/api/health/>
- Django admin: <http://127.0.0.1:8000/admin/>

When `DEBUG=True` and `SECRET_KEY` is empty, a development-only key is used. Setting `DEBUG=False` requires a real `SECRET_KEY`.

### 2. Frontend

```powershell
cd frontend
copy .env.example .env.local      # macOS/Linux: cp .env.example .env.local
npm install
npm run dev
```

Open <http://localhost:3000>. The client calls the API at `VITE_API_BASE_URL`, which defaults to `http://127.0.0.1:8000/api/v1`.

### 3. Train the models

Claims are only scored when trained models exist in `backend/ml/models/`. From `backend/django_backend`:

```powershell
python manage.py train_project_models
```

See [Machine learning](#machine-learning) for what each command produces.

### 4. Demo in one command

For a 5-minute walkthrough, run this from `backend/django_backend` after `migrate` and the training step:

```powershell
python manage.py load_demo            # safe to run again; nothing is duplicated
python manage.py load_demo --reset    # delete the demo data (only the demo data) and recreate it
```

It creates 3 customers in Bengaluru, Gurugram and Chennai with Indian cars and active policies, 7 claims that show the AI at work (an honest fender-bender, an inflated repair bill, a late claim on a brand-new policy, a night-time theft with no FIR under investigation, a flood write-off, a windshield and a three-car accident with injuries), and scores every claim with the AI models. Log in with:

| Role | Where | Login |
| --- | --- | --- |
| Admin | Staff login | `admin@demo.insurex.test` / `InsureX@Demo2026` |
| Employee | Staff login | `employee@demo.insurex.test` / `InsureX@Demo2026` |
| Investigator | Staff login | `investigator@demo.insurex.test` / `InsureX@Demo2026` |
| Customer | Customer sign-in | `customer@demo.insurex.test`, then the 6-digit code emailed to it |

Customers sign in with a one-time code sent to their email (password sign-in is still offered). With the default console email backend, the code is printed in the `runserver` terminal. Use `--password` to choose a different staff password. The command refuses to run when `DEBUG=False`, because it creates accounts with a known password; `--allow-production` overrides that.

### 5. Load the sample datasets (optional)

To import the bundled sample datasets, run this from `backend/django_backend`:

```powershell
python manage.py import_project_datasets --dry-run   # validate CSVs only
python manage.py import_project_datasets
python manage.py seed_routing_demo_agents            # demo staff profiles for routing advice
```

The importer is idempotent, so you can run it again safely. See [docs/DATASETS.md](docs/DATASETS.md) for details.

## Background jobs

Celery runs three jobs:

| Job | When |
| --- | --- |
| `score_claim_async` | Each new claim, so FNOL doesn't wait for the models |
| `check_policy_expirations` | Daily, through Celery beat |
| `send_renewal_reminders` | Daily, through Celery beat |

With Redis running and `CELERY_BROKER_URL` set, start the worker and the scheduler from `backend/django_backend`, each in its own terminal:

```powershell
celery -A config worker -l info --pool=solo   # --pool=solo is needed on Windows
celery -A config beat -l info
```

You don't need Redis to develop. If the broker can't be reached, a new claim is scored inside the request instead, so a queue outage never blocks a claim from being saved. Set `CELERY_TASK_ALWAYS_EAGER=True` to run every task in-process. `manage.py test` always runs tasks in-process.

## API overview

All endpoints are under `/api/v1/` and use JWT bearer auth.

| Prefix | Area |
| --- | --- |
| `auth/` | Register, staff login, customer `customer-login/request-code/` and `verify-code/`, token refresh, profile |
| `customers/` | Customers and callback requests |
| `policies/` | Policies, `quote/`, `bind-quote/`, premium history, endorsements |
| `vehicles/` | Vehicles |
| `claims/` | Claims / FNOL |
| `assessments/` | Assessments and routing advisory |
| `workforce/` | `employees/` list and employee profiles |
| `investigations/` | Investigations and outcomes |
| `settlements/` | Settlements |
| `notifications/` | Notifications |
| `analytics/` | Dashboard analytics |
| `ai/` | AI endpoints, e.g. `assess-claim/` |
| `audit/audit-events/` | Staff audit history for policy, claim, investigation, and settlement changes |

Swagger UI has the full, authoritative list. The policy and claim workflow is described in [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Machine learning

InsureX is moving to the US market (see [docs/US_MIGRATION_PLAN.md](docs/US_MIGRATION_PLAN.md)). Until Phase 3 of that plan, `train_project_models` trains on the original US-dollar files `backend/data/insurance_claims.csv` and `backend/data/fraud_oracle.csv`.

The US training and benchmark data is the synthetic **Lumora Mutual** book, made by the `motorsynth` generator in `backend/data/us/`. Generated files aren't committed. To make the 50K sample, from `backend/data/us`:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m motorsynth.generate config.yaml --terms 50000 --out sample
.venv\Scripts\python.exe checks.py sample
```

The fixed seed in `config.yaml` makes the output identical on every run. It writes the observable tables plus `ground_truth/`, `STORY.md` and `VALIDATION.md` to `backend/data/us/sample/`. `ground_truth/` is for training and benchmarking only and must never be loaded into the app database. Leave out `--terms` to generate the full book of about 1M policy terms.

The training commands write these artifacts to [backend/ml/models/](backend/ml/models/):

| Artifact | Purpose | Trained by |
| --- | --- | --- |
| `fraud_risk.joblib`, `fraud_oracle_fraud.joblib` | Fraud-risk classifiers | `train_project_models` |
| `repair_cost.joblib` | Repair-cost regression | `train_project_models` |
| `total_loss.joblib` | Total-loss classifier | `train_project_models` |
| `training_report.json`, `fraud_oracle_evaluation.png` | Metrics and evaluation charts | `train_project_models` |
| `vehicle_fraud.joblib`, `vehicle_fraud_report.json` | Vehicle-level fraud model and its report | `train_vehicle_fraud_model` (no US dataset yet; returns in Phase 3) |

To retrain and re-score, from `backend/django_backend`:

```powershell
python manage.py train_project_models
python manage.py assess_claims          # re-score existing claims with the new models
```

New claims are scored automatically when they are submitted (see [Background jobs](#background-jobs)).

**If training crashes on Windows** with `Bad file descriptor (...libzmq...epoll.cpp:100)` after the models are trained, turn off joblib's worker processes for that run. Training is slower but finishes:

```powershell
$env:JOBLIB_MULTIPROCESSING = "0"; python manage.py train_project_models
``` To export investigator outcomes for retraining on real labels, use `python manage.py export_claim_outcomes`.

### Triage priority score

The stored `fraud_risk_score` is the **Triage Priority Score (Heuristic v1)**. It combines the model score with the rule-based red flags in `apps/assessments/triage_heuristic_v1.json`. A high score means "review first", not "fraud". A fraud finding is recorded only when an investigator completes a case with an outcome, which also sets the claim's `fraud_outcome`. Customers never receive any score field. See [docs/TRIAGE_SCORE_ROLLOUT.md](docs/TRIAGE_SCORE_ROLLOUT.md).

### RL claim routing

- RL claim-routing simulator (training, evaluation gate, deployment): [backend/rl/README.md](backend/rl/README.md)

RL routing is **advisory only**. It never assigns claims. Recommendations stay disabled until a PPO artifact passes the evaluation gate (`CLAIM_ROUTING_ENFORCE_EVALUATION_GATE`).

## Configuration

Backend settings are read from environment variables. Use `backend/django_backend/.env` locally. Key variables:

| Variable | Default | Notes |
| --- | --- | --- |
| `DEBUG` | `True` | Set to `False` in production |
| `SECRET_KEY` | dev key when `DEBUG=True` | Required when `DEBUG=False` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | Comma-separated |
| `DATABASE_URL` | — | Takes precedence over the settings below when set |
| `DATABASE_ENGINE` / `POSTGRES_*` | SQLite | Postgres settings used when no `DATABASE_URL` is set |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_URL` | `http://localhost:3000` | Frontend origin(s) |
| `USE_X_FORWARDED_PROTO` | `False` | Set to `True` behind a TLS-terminating proxy |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Redis for background jobs |
| `CELERY_TASK_ALWAYS_EAGER` | `False` | `True` runs tasks in-process with no broker |
| `USE_S3_STORAGE`, `AWS_*` | `False` | S3-compatible storage for uploads (S3, Cloudflare R2, Supabase) |
| `CLAIM_ANNUAL_DEPRECIATION_RATE`, `CLAIM_MAX_DEPRECIATION_RATE` | `0.05`, `0.80` | Settlement depreciation |
| `ML_CURRENCY_PER_DATASET_UNIT` | `1` | Keep `1`: the models are trained on US-dollar data |
| `CLAIM_ROUTING_MODEL_PATH`, `CLAIM_ROUTING_ENFORCE_EVALUATION_GATE` | — | RL routing artifact and evaluation gate |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | `60`, `7` | Token lifetimes |
| `EMAIL_*` | console backend | SMTP settings; also used to send customer sign-in codes |
| `CUSTOMER_LOGIN_CODE_TTL_MINUTES`, `CUSTOMER_LOGIN_CODE_MAX_ATTEMPTS` | `10`, `5` | Lifetime of a customer sign-in code, and wrong guesses allowed |
| `THROTTLE_LOGIN_CODE_RATE` | `10/hour` | Sign-in code requests per IP address |
| `LOG_LEVEL` | `INFO` | Log level |

Premium rating is not set through environment variables. The tables (third-party premium by engine size, depreciation, NCB, own-damage rates, add-ons, GST) are in `POLICY_RATING_TABLES` in `config/settings.py`, and each figure is marked `SPEC` or `PLACEHOLDER`.

The frontend reads `VITE_API_BASE_URL`.

Never commit `.env` files or real secrets.

## Testing and quality checks

CI runs these checks (see [Jenkinsfile](Jenkinsfile)):

```powershell
# Frontend
cd frontend
npm run lint
npm run build

# Backend (from backend/django_backend)
python manage.py check
python manage.py spectacular --validate --file openapi-schema.yml
python manage.py test

# RL package tests (from backend)
python -m pytest rl/tests
```

The frontend also has Vitest unit tests, which CI does not run yet:

```powershell
cd frontend
npm test
```

CI also generates the 50K Lumora sample from `backend/data/us/` and runs its integrity checks (`checks.py`) before training the models.

## Deployment

- **API:** Render, using [render.yaml](render.yaml). It needs a PostgreSQL `DATABASE_URL`.
- **Frontend:** Vercel, with SPA rewrites in `frontend/vercel.json`. Set `VITE_API_BASE_URL` to the Render API URL and redeploy.

`render.yaml` deploys only the web service. It has no Redis, Celery worker or beat, so on Render claims are scored inside the request and the daily expiry and renewal-reminder jobs don't run. To get them, add a Redis instance plus worker and beat services and set `CELERY_BROKER_URL`.

For step-by-step instructions, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Render's free tier has an ephemeral filesystem, so set `USE_S3_STORAGE=true` with an S3-compatible bucket before you rely on uploaded claim documents in production.

## License

[MIT](LICENSE) © 2026 Mohammad Adnan PM
