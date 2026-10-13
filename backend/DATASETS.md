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

The importer can be rerun safely; it updates the records it previously imported. To validate the CSV headers and row counts without changing the database, run:

```powershell
python manage.py import_project_datasets --dry-run
```

The import maps claim dates, severity, amounts, incidents, injuries, witnesses, police reports, vehicle details, policy premiums and deductibles, and fraud labels into the existing Django models. Each original CSV row is also retained under `Claim.ai_assessment.source_data`. Fraud-labeled rows are marked for investigation; other historical records are marked closed. Imported account records are inactive and use generated dataset addresses, not customer sign-in accounts.

The existing claims, policies, vehicles, fraud, and analytics APIs expose the imported records to the application. Staff views can see the dataset claims; customer views remain limited to claims owned by the signed-in customer.
