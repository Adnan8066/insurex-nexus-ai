# Project datasets

The backend includes two historical sample datasets:

- `insurance_claims.csv` (1,000 records)
- `fraud_oracle.csv` (15,420 records)

`fraud_oracle-selected-columns.csv` is generated from the full Fraud Oracle file and contains the selected 10-column view. The full source file is used for importing because it also contains the fraud label and claim fields.

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
