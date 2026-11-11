# Indian motor claims dataset (synthetic)

Simulated Indian private-car own-damage claims, written in the layout each model in the
project trains on. Regenerate with:

```bash
python generate_india_claims.py --rows 20000 --seed 7
```

> **Synthetic, not real claims.** The rules below come from public Indian regulation and
> documented motor-fraud patterns, but every cost and fraud rate is an assumption written in
> `generate_india_claims.py`. A model trained here learns those assumptions, so its scores on
> this data are optimistic about its scores on real claims. Use it to build, test and demo the
> pipeline. Before relying on the scores, retrain on settled claims with investigator outcomes
> (`Claim.fraud_outcome`).

## Files

| File | Layout of | Trains |
|---|---|---|
| `india_claims_master.csv` | every simulated field, including the hidden truth (`is_fraud_truth`, `fraud_scheme`) | analysis only |
| `india_insurance_claims.csv` | `insurance_claims.csv` plus `total_loss_outcome` | `fraud_risk`, `repair_cost`, `total_loss` |
| `india_fraud_oracle.csv` | `fraud_oracle.csv` | `fraud_oracle_fraud` |
| `india_vehicle_fraud.csv` | `apps/assessments/vehicle_fraud.py` features + `fraud_outcome` | `vehicle_fraud` |

Training commands (from `backend/django_backend`). `train_project_models` uses these Indian files by default:

```bash
python manage.py train_project_models
```

```bash
python manage.py train_vehicle_fraud_model --dataset ../data/india/india_vehicle_fraud.csv
```

**Amounts are in rupees.** `ML_CURRENCY_PER_DATASET_UNIT` defaults to `1`, which matches models
trained on this data. Set it to `83` only if you restore models trained on the US-dollar files.

## What is simulated

- **Vehicles:** 41 Indian models (Maruti Suzuki, Hyundai, Tata, Mahindra, Kia, Toyota, Honda, MG,
  Renault, Skoda, VW, and a little BMW/Mercedes). Approximate 2024 ex-showroom prices, with a
  variant spread of −10% to +25%. Fuel types use the app's values (`gasoline`, `diesel`, `hybrid`,
  `electric`). CNG isn't modelled because the app has no CNG choice.
- **IDV:** ex-showroom price × (1 − IRDAI depreciation for vehicle age), the same rule as
  `repair_estimate.py`.
- **Premium:** own-damage tariff rate × IDV, less NCB and a market discount, plus the IRDAI
  third-party premium for the engine size (₹2,094 / ₹3,416 / ₹7,897), plus 18% GST. The
  zero-depreciation add-on costs about 18% more own-damage premium.
- **Deductible:** compulsory ₹1,000 (≤1500 cc) or ₹2,000 (>1500 cc), plus an optional voluntary
  deductible.
- **Places:** 35 cities across 3 tiers. Labour costs are 15% higher in tier-1 cities and 12% lower
  in tier-3. Flood claims cluster in monsoon states from June to September. Fraud does **not**
  depend on the city; organised fraud is tied to a few garages instead.
- **Repair cost (`vehicle_claim` / `assessed_repair_cost_inr`):** the surveyor-assessed loss, not
  the amount claimed. It is calibrated to real Indian part and labour prices in `reference/`, the
  same rates as `apps/assessments/repair_estimate.py`: body-shop labour (₹4,500–17,500 by severity
  and hatchback/sedan vs SUV/MUV) plus a parts share of the ex-showroom price (0.2% minor, 1.2%
  moderate, 4% major, 0.7% windshield). Labour varies ±25% and parts ±45% log-normally, and both
  shift with city tier, incident type, luxury make and EV battery damage. A repair above 75% of
  IDV becomes a constructive total loss settled at the IDV. A quarter of major repairs carry hidden
  structural, airbag or engine damage (parts ×2–6). Median results: minor ₹8,000, moderate ₹18,000,
  major about ₹70,000.
- **Reported severity vs total-loss outcome:** customers pick a severity on the claim form and
  misjudge it by one level 15% of the time. The surveyor's decision is a separate outcome
  (`total_loss_outcome` in the insurance layout, `is_total_loss` in the master file). A reported
  total loss is confirmed about 90% of the time; a reported major crash becomes a total loss about
  1% of the time (6% for cars 8+ years old). All layouts carry the reported severity, which is what
  the app knows when it scores a claim.
- **App repair estimate (`app_repair_estimate_inr`):** the app's formula with no noise, used for the
  vehicle-fraud feature `claim_to_repair_ratio`.
- **Fraud (about 8% of claims):** propensity rises with a policy started within 45 days, earlier
  claims, an old vehicle, no NCB, a zero-dep cover and a ring garage, plus random noise. Each
  fraud follows one scheme:

| Scheme | Share | Signals it leaves (honest claims show them at lower rates too) |
|---|---|---|
| Inflated bill | ~42% | claim 1.4–3.2× the assessed cost, more supplementary estimates |
| Pre-existing damage | ~16% | policy bought 1–30 days earlier, late reporting, photos dated before the incident |
| Staged accident | ~14% | multi-vehicle, night-time, injury claims, friendly witnesses |
| Recycled photos | ~12% | reused, edited, low-resolution photos or photos with no camera date |
| Fake theft | ~9% | no or late FIR, late reporting, night-time, old vehicle |
| Arson / flood dump | ~7% | fire or flood total loss on an older car |

- **Reporting delay:** 80% of honest claims are reported within about 3 days, 17% after 4–21 days
  and 3% after 22–45 days. Fraud schemes add further delay, so a late report raises risk (claims
  reported 8–12 days late are about twice as likely to be fraud) without proving it.
- **Label noise:** investigators catch 88% of fraud and wrongly flag 1% of honest claims.
  `fraud_outcome` / `fraud_reported` / `FraudFound_P` carry this observed label, and
  `is_fraud_truth` in the master file holds the truth.

## Known limits

- Repair costs are calibrated to real part list prices and workshop labour rates, but not to real
  settled claims. The major-damage parts share doubles the visible-parts figure to allow for
  hidden damage, which is an assumption.
- Fraud figures are not fitted to real settlements either. Replace them with insurer or app data as soon
  as it exists.
- The insurance layout keeps the app's category mapping (`ai_views.py`), which folds fire, flood,
  glass and similar types into `Other`. Those types are visible only in the vehicle-fraud layout
  and the master file.
- `Fault`, `AgentType` and `NumberOfCars` in the oracle layout are filler with little meaning.
