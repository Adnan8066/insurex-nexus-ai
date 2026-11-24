# Triage priority score: meaning and rename plan

## What the score means

The **Triage Priority Score (Heuristic v1)** is the value stored in the database
field `fraud_risk_score`. It combines the model score with rule-based red flags
(`apps/assessments/triage_heuristic_v1.json`).

- A **High Triage Priority** claim is one where the score crossed the review
  threshold. It is a review-prioritisation and routing signal. It is **not** a
  fraud verdict.
- A fraud finding is recorded only by the investigator, as an **investigation
  outcome**: `confirmed_fraud`, `cleared`, `inconclusive`, or `pending` until the
  case is completed.

## What the API exposes today

| Where | Fields |
|---|---|
| Claim detail (staff) | `fraud_risk_score` (kept), `triage_priority_score`, `heuristic_version` |
| Assessment | `fraud_risk_score` (kept), `triage_priority_score`, `triage_heuristic_version` |
| Investigation | `triage_priority_score`, `heuristic_version`, `investigation_outcome`, `outcome_notes`, `outcome_reviewed_at` |

Customers never receive any of the score fields. The claim serializer removes
`ai_assessment`, `fraud_risk_score`, `triage_priority_score`, `heuristic_version` and
`total_loss_probability` for customer requests.

## Claim-level outcome sync

When an investigator completes a case with an outcome, the claim's existing
`fraud_outcome` is set to match, and the outcome export reads it:

| Investigation outcome | Claim `fraud_outcome` |
|---|---|
| `confirmed_fraud` | `fraud` |
| `cleared` | `genuine` |
| `inconclusive` | `unclear` |
| `pending` | unchanged |

## Rename rollout (not started)

Renaming the database column and the API field can break existing clients, so the
rename happens in four releases:

1. **Add** a `triage_priority_score` column (`DecimalField`, nullable) to
   `ClaimAssessment` and `Claim`, with a migration.
2. **Backfill** it from `fraud_risk_score` in a data migration, in batches.
3. **Switch readers** to `triage_priority_score` and keep a fallback to
   `fraud_risk_score` for rows where it is empty. Writers fill both columns.
4. **Deprecate and remove** `fraud_risk_score` once no client reads it. Give
   clients a release window and check the API logs for remaining readers first.

Until step 1 ships, `triage_priority_score` is a read-only alias in the serializers.

## MLflow (separate, later)

Once real `confirmed_fraud` and `cleared` outcomes exist, log the heuristic version,
thresholds, and evaluation metrics to MLflow as a separate milestone.
