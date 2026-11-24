# Policy-to-claim workflow

This Django API now provides a connected demonstration workflow. The premium
and depreciation factors below are configurable examples, not actuarially
approved rates or policy wording. Replace them with approved product rules
before using the platform for real insurance business.

## Policy intake, quote, and issuance

1. Staff enters the customer, applicant/asset details, risk factors, declared
   asset value, coverage limit, deductible, risk score, and requested terms in
   the policy form.
2. `POST /api/v1/policies/quote/` persists a `PolicyApplication` and returns the
   annual premium with a line-by-line breakdown. The server calculates it from the
   vehicle record, so the request's own value and risk score are ignored:
   - **Insured value (IDV)** = ex-showroom price × (1 − depreciation). Depreciation
     by vehicle age, from the model year: 5% (0 years), 15% (1), 20% (2), 30% (3),
     40% (4), 50% (5 or more).
   - **Third-party premium** by engine capacity: under 1,000 cc ₹2,094; 1,000–1,500 cc
     ₹3,416; above 1,500 cc ₹7,897.
   - **Own-damage premium** = IDV × OD rate: Zone A (listed metro cities) 3.0%,
     Zone B 2.5%.
   - **No-claim bonus discount** on the own-damage premium only: 0%, 20%, 25%, 35%,
     45%, 50% for 0 to 5+ claim-free years (entered on the request).
   - **Add-ons**: priced as a share of IDV or a fixed amount (chosen on the request).
   - **Compulsory personal accident cover**: ₹350, when a third-party cover is included.
   - **Subtotal** = sum of the lines above. **GST** = 18% of the subtotal. The total is
     the quoted premium.

   Plans include different lines: Third Party Liability Only = third-party + personal
   accident; Comprehensive = all lines; Standalone Own Damage = own-damage and add-ons
   (no third-party line, since it needs a separate third-party policy).

   All rates live in `POLICY_RATING_TABLES` in `config/settings.py`. Items marked
   PLACEHOLDER there (OD rates, Zone A cities, add-on prices, the ₹350 personal accident
   premium, and depreciation above 5 years) are not from the product spec and must be
   replaced with approved insurer figures. Each quote carries
   `tariff_source: INDICATIVE_DEMO_TARIFF`, and the screens show an "Indicative / Demo
   Tariff" badge.
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

## Claim state machine and settlements

Claim statuses: `submitted → under_review → ai_assessment → investigation →
approved / rejected → repair_settlement → closed`.

- Only employees and admins can approve or reject (`claims/workflow.py`).
- A claim cannot be approved while it is still `submitted` or in `investigation`.
- A high-risk claim (fraud score above 65) needs a completed investigation before
  approval.
- Each status change writes a status history entry and a timeline entry, and notifies
  the customer.

Settlements (`/api/v1/settlements/`) record the repair payout for an approved claim.
Statuses: calculated → under review → approved / rejected → paid. Payment statuses:
pending, processing, completed, failed, refunded. The payout is:

```
depreciation = 0 if zero-depreciation add-on, else repair cost × min(0.05 × vehicle age, 0.80)
payout       = max(0, repair cost − deductible − depreciation)
```

The 5% per year and 80% cap are `CLAIM_ANNUAL_DEPRECIATION_RATE` and
`CLAIM_MAX_DEPRECIATION_RATE` in settings. Staff create, approve, reject, pay and
complete payments; customers can read their own settlements.

## Background jobs

Run these from `backend/django_backend` once Redis is running and `CELERY_BROKER_URL`
points at it:

```powershell
celery -A config worker -l info
celery -A config beat -l info
```

- `apps.assessments.tasks.score_claim_async`: scores a new claim after FNOL. It is
  skipped if the claim already has a completed score since it was submitted. If the
  queue cannot be reached, the claim is scored in the request instead.
- `apps.policies.tasks.check_policy_expirations`: marks policies past their end date
  as expired. Running it again changes nothing.
- `apps.policies.tasks.send_renewal_reminders`: sends one reminder each at 30, 15 and
  7 days before the end date. Each reminder is sent once.

Beat runs both policy jobs once a day (`CELERY_BEAT_SCHEDULE` in settings). Tests and
any run with `CELERY_TASK_ALWAYS_EAGER=true` execute tasks in-process, so no Redis is
needed for them.

## Operations

Run migrations with:

```powershell
python backend/django_backend/manage.py migrate
```

Review the premium tables in `POLICY_RATING_TABLES` (`config/settings.py`) for each
deployment. The current values are demonstration values, and the PLACEHOLDER items
must be replaced before live use. A live pilot
also requires approved product-specific rules, real staff routing profiles,
qualified model weights and evaluation report.
