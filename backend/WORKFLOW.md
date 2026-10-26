# Policy-to-claim workflow

This Django API now provides a connected demonstration workflow. The premium
and depreciation factors below are configurable examples, not actuarially
approved rates or policy wording. Replace them with approved product rules
before using the platform for real insurance business.

## Policy intake, quote, and issuance

1. Staff enters the customer, applicant/asset details, risk factors, declared
   asset value, coverage limit, deductible, risk score, and requested terms in
   the policy form.
2. `POST /api/v1/policies/quote/` persists a `PolicyApplication` and returns a
   versioned annual premium estimate and calculation breakdown. The default
   rating formula is configured by `POLICY_BASE_ANNUAL_RATE` and
   `POLICY_DEDUCTIBLE_CREDIT_RATE`; `POLICY_RATING_VERSION` identifies it.
3. Staff reviews the result and selects **Issue Active Policy**. The frontend
   calls `POST /api/v1/policies/bind-quote/` with `application_id`. The API
   binds the quote to an active policy and creates its first premium history
   installment. Existing policy CRUD remains available for administration.

## Billing and endorsements

- Premium history is available from `GET /api/v1/policies/{id}/premium-history/`.
- Staff submits proposed changes at
  `POST /api/v1/policies/{id}/endorsements/`. Supported fields include
  `coverage`, `deductible`, `premium_delta`, and `assets_add` (each asset needs
  a description and positive value).
- An administrator applies a pending request using
  `POST /api/v1/policies/{id}/endorsements/{endorsement_id}/approve/`, or rejects
  it using the corresponding `/reject/` endpoint. Before/after snapshots and
  reviewer identity are retained. Premium adjustments create a pending billing
  history entry.

## FNOL and routing advice

- FNOL accepts `estimated_repair_cost`; the claim's complexity score is derived
  from incident metadata and stored for routing.
- RL routing is advisory only. Recommendation/review endpoints do not assign a
  claim. Production recommendations remain disabled until a PPO artifact and
  its evaluation report pass the configured gate. See `rl/README.md` for the
  simulator, evaluation report, and deployment requirements.

## Operations

Run migrations with:

```powershell
python backend/django_backend/manage.py migrate
```

Set rating and depreciation settings through environment variables in each
deployment. The current default factors are demonstration values. A live pilot
also requires approved product-specific rules, real staff routing profiles,
qualified model weights and evaluation report.
