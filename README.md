# InsureX Nexus AI

An AI-assisted motor insurance platform covering the policy-to-claim lifecycle: policy quoting and issuance, vehicle records, first notice of loss (FNOL), claim tracking, fraud scoring, investigations, and an advisory reinforcement-learning (RL) claim-routing simulator.

- **Frontend:** React 18 + Vite + Tailwind CSS (deployed on Vercel)
- **Backend:** Django 5 + Django REST Framework, JWT auth, OpenAPI docs (deployed on Render)
- **ML:** scikit-learn / LightGBM tabular models, Stable-Baselines3 PPO for routing advice

> **Demonstration only.** Premium rates, depreciation factors, and policy tiers are illustrative values, not actuarially approved figures. The RL routing data is synthetic. Fraud scores rank claims for review and are never proof of fraud. Every AI output is advisory and needs a human decision.

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
│       ├── layouts/              Page shells
│       ├── pages/                One folder per area (claims, policies, ai, fraud, ...)
│       ├── routes/               Route table and role guards
│       ├── services/             API client, one module per backend area
│       └── utils/                Formatting and permission helpers
├── backend/
│   ├── django_backend/           Django project
│   │   ├── config/               Settings, URLs, WSGI/ASGI
│   │   ├── apps/                 Domain apps (see below)
│   │   ├── common/               Permissions, errors, uploads, risk bands
│   │   ├── ml_service.py         Loads trained models and scores claims
│   │   └── manage.py
│   ├── data/                     Datasets
│   │   ├── insurance_claims.csv  1,000 claims (fraud, repair cost, total loss)
│   │   ├── fraud_oracle.csv      15,420 claims (fraud)
│   │   └── demo/                 Anonymized demo vehicle/policy CSVs
│   ├── ml/models/                Trained model artifacts and training report
│   ├── rl/                       Claim-routing RL simulator, training, evaluation
│   └── requirements.txt          Points to django_backend/requirements.txt
├── docs/
│   ├── PROJECT_REFERENCE.md      Full code-level reference
│   ├── WORKFLOW.md               Policy → quote → claim workflow and endpoints
│   ├── DATASETS.md               Dataset import and model training
│   └── DEPLOYMENT.md             Render + Vercel deployment
├── render.yaml                   Render Blueprint for the API
└── Jenkinsfile                   CI: frontend lint/build, backend check/schema/tests
```

### Backend apps

| App | Responsibility |
| --- | --- |
| `accounts` | Custom user model, JWT auth, roles |
| `customers` | Customer profiles, callback requests |
| `policies` | Policy applications, quotes, binding, premium history, endorsements |
| `vehicles` | Insured vehicle records |
| `claims` | FNOL, claim lifecycle, dataset import and model training commands |
| `assessments` | AI assessment, automated review, RL routing advisory |
| `investigations` | Fraud alerts and investigation cases |
| `settlements` | Payout calculation with depreciation (not yet enabled in `INSTALLED_APPS`) |
| `notifications` | In-app notifications |
| `analytics` | Dashboard metrics |

User roles: `customer`, `employee`, `investigator`, `admin`. Each role gets its own dashboard in the frontend.

## Prerequisites

- Python 3.12 (the version used by CI and Render)
- Node.js 18+ and npm
- Optional: PostgreSQL. SQLite is used by default for local development.

## Quick start (local development)

### 1. Backend API

```powershell
cd backend/django_backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
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

### 3. Load demo data (optional)

The database starts empty. To import the bundled sample datasets, run this from `backend/django_backend`:

```powershell
python manage.py import_project_datasets --dry-run   # validate CSVs only
python manage.py import_project_datasets
python manage.py seed_routing_demo_agents            # demo staff profiles for routing advice
```

The importer is idempotent, so you can run it again safely. See [docs/DATASETS.md](docs/DATASETS.md) for details.

## API overview

All endpoints are under `/api/v1/` and use JWT bearer auth.

| Prefix | Area |
| --- | --- |
| `auth/` | Register, login, token refresh, profile |
| `customers/` | Customers and callback requests |
| `policies/` | Policies, `quote/`, `bind-quote/`, premium history, endorsements |
| `vehicles/` | Vehicles |
| `claims/` | Claims / FNOL |
| `assessments/` | Assessments and routing advisory |
| `investigations/` | Investigations |
| `notifications/` | Notifications |
| `analytics/` | Dashboard analytics |
| `ai/` | AI endpoints, e.g. `assess-claim/` |

Swagger UI has the full, authoritative list. The policy and claim workflow is described in [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Machine learning

Trained artifacts live in [backend/ml/models/](backend/ml/models/):

| Artifact | Purpose |
| --- | --- |
| `fraud_risk.joblib`, `fraud_oracle_fraud.joblib` | Fraud-risk classifiers |
| `repair_cost.joblib` | Repair-cost regression |
| `total_loss.joblib` | Total-loss classifier |
| `training_report.json`, `fraud_oracle_evaluation.png` | Metrics and evaluation charts from the last training run |

Retrain the tabular models from `backend/django_backend`:

```powershell
python manage.py train_project_models   # trains from backend/data/
python manage.py assess_claims          # re-score existing claims with the new models
```

New claims are scored automatically when they are submitted.

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
| `POLICY_BASE_ANNUAL_RATE`, `POLICY_DEDUCTIBLE_CREDIT_RATE`, `POLICY_RATING_VERSION` | `0.025`, `0.20`, `demo-v1` | Demo rating formula |
| `CLAIM_ANNUAL_DEPRECIATION_RATE`, `CLAIM_MAX_DEPRECIATION_RATE` | `0.05`, `0.80` | Settlement depreciation |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | `60`, `7` | Token lifetimes |
| `EMAIL_*` | console backend | SMTP settings |

The frontend's only variable is `VITE_API_BASE_URL`.

Never commit `.env` files or real secrets.

## Testing and quality checks

These are the same checks CI runs (see [Jenkinsfile](Jenkinsfile)):

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

## Deployment

- **API:** Render, using [render.yaml](render.yaml). It needs a PostgreSQL `DATABASE_URL`.
- **Frontend:** Vercel, with SPA rewrites in `frontend/vercel.json`. Set `VITE_API_BASE_URL` to the Render API URL and redeploy.

For step-by-step instructions, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Render's free tier has an ephemeral filesystem, so uploaded claim documents need persistent storage before you rely on them in production.

## License

[MIT](LICENSE) © 2026 Mohammad Adnan PM
