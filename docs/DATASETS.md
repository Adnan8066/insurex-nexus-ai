# Project datasets

The backend includes two historical sample datasets in `backend/data/`:

- `insurance_claims.csv` (1,000 records)
- `fraud_oracle.csv` (15,420 records)

`backend/data/demo/` holds small anonymized vehicle and policy CSVs for demonstrations.

From `backend/django_backend`, apply migrations and load the records with:

```powershell
python manage.py migrate
python manage.py import_project_datasets
```

Train the app's models from the same datasets with:

```powershell
python manage.py train_project_models
```

This trains fraud detection, repair-cost, and total-loss models from `insurance_claims.csv`, and a separate fraud model from the full `fraud_oracle.csv`. Fraud Oracle has no repair-cost or total-loss target, so it is used for fraud classification only. The Fraud Oracle model uses LightGBM with `scale_pos_weight=3`, sigmoid probability calibration, and a threshold selected on a validation split to maximize precision while meeting at least 75% recall in the 0.05–0.50 threshold range. A separate stratified 20% test split is used once for reported metrics; the final model is then refit on all rows. The report includes the previous-model comparison, confusion matrices, threshold sweep, dataset/target audit, and feature-timing caveat. Curves and confusion matrices are saved to `backend/ml/models/fraud_oracle_evaluation.png`. The selected high-recall threshold increases false alerts; fraud scores are review priorities, never proof of fraud.

The importer can be rerun safely; it updates the records it previously imported. To validate the CSV headers and row counts without changing the database, run:

```powershell
python manage.py import_project_datasets --dry-run
```

The import maps claim dates, severity, amounts, incidents, injuries, witnesses, police reports, vehicle details, policy premiums and deductibles, and fraud labels into the existing Django models. Each original CSV row is also retained under `Claim.ai_assessment.source_data`. Fraud-labeled rows are marked for investigation; other historical records are marked closed. Imported account records are inactive and use generated dataset addresses, not customer sign-in accounts.

The existing claims, policies, vehicles, fraud, and analytics APIs expose the imported records to the application. Staff views can see the dataset claims; customer views remain limited to claims owned by the signed-in customer.

The policy creation form includes eight user-provided motor policy tier examples (`POL-PC-001`–`POL-PC-006` and `POL-TW-007`–`POL-TW-008`). Their base premiums are illustrative estimates only; they are not verified insurer quotes or offers. Selecting a tier stores its ID and coverage summary with the created policy.


## Synthetic RL transition data

`rl/data/synthetic_claim_routing_transitions.csv` contains 20,000 synthetic
state/action/reward/next-state transitions for the claim-routing simulator. It
uses the observation layout and reward assumptions documented in
`rl/environment.py`; `episode_id` and `step` preserve trajectory boundaries.
This is suitable for exercising offline-RL data pipelines and inspecting the
simulator's behavior. It is **not real insurance or adjuster-performance data**
and cannot establish real-world routing quality. Regenerate it with the
`least_workload` behavior policy before the updated PPO training workflow uses
the CSV to warm-start its actor by imitating those heuristic actions. PPO then
continues learning by interacting with the simulator; logged rewards are not
used in the warm start.

Regenerate it from the `backend` directory with:

```powershell
python -m rl.generate_dataset --episodes 200 --steps 100 --seed 2026 --policy least_workload
```
