# Training the fraud model on Lumora data

This trains a claim fraud model on the synthetic **Lumora** US data and compares it with red-flag rules. It's an offline experiment for Phase 3 of [US_MIGRATION_PLAN.md](../../../docs/US_MIGRATION_PLAN.md). **The app doesn't use this model**: live scoring in `ml_service.py` stays unchanged until Phases 2 and 3 are done.

All commands are for PowerShell on Windows.

## Step 1: Put the full Lumora book in place

You need the **full 1M Lumora book**: a folder with `claims.parquet`, `vehicles.parquet`, `siu_investigations.parquet` and a `ground_truth\` folder, among others.

**Use the downloaded folder** (`Downloads\lumora_full_1M_parquet 1 (1)`, 148,020 claims). Copy it into the project as `backend\data\us\lumora_full`. Git ignores that folder, and the commands below use it:

```powershell
Copy-Item -Recurse "C:\Users\Mohammad.Adnan\Downloads\lumora_full_1M_parquet 1 (1)" "D:\InsureX Nexus AI\backend\data\us\lumora_full"
```

Check that the important files arrived:

```powershell
Test-Path "D:\InsureX Nexus AI\backend\data\us\lumora_full\vehicles.parquet", "D:\InsureX Nexus AI\backend\data\us\lumora_full\siu_investigations.parquet", "D:\InsureX Nexus AI\backend\data\us\lumora_full\ground_truth\truth_claims.parquet"
```

All three lines must say `True`. If `lumora_full` already existed before the copy, PowerShell puts the folder *inside* it, and the checks fail. Delete the old `lumora_full` and copy again.

**Or use the book you generated.** `backend\data\us\output` already holds a full book you generated on 2026-11-24 (999,532 terms, 147,999 claims). It works too: use `data\us\output` in place of `data\us\lumora_full` in Step 3. Its counts differ slightly from the download, probably because of different library versions, so compare runs on the same folder.

> Don't use `lumora_full_1M_parquet.zip`. That download is **truncated**: it can't be opened, and it's missing `vehicles`, `siu_investigations` and `ground_truth/`.

<details>
<summary>No downloaded folder? Generate the book instead</summary>

The generator uses a fixed seed (`20261120` in `config.yaml`), so it produces the same book. It needs plenty of memory (16 GB of RAM or more is safest). From `backend\data\us`:

```powershell
py -3.12 -m venv .venv
```

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```powershell
.venv\Scripts\python.exe -m motorsynth.generate config.yaml --out output --no-csv
```

```powershell
.venv\Scripts\python.exe checks.py output
```

If it runs out of memory, use `--terms 300000 --out output_300k` and use that folder in Step 3.

</details>

## Step 2: Set up the training environment (once)

Use the backend's own environment, so the LightGBM and scikit-learn versions match the app (`lightgbm==4.7.0`, `scikit-learn==1.9.1`):

```powershell
cd "D:\InsureX Nexus AI\backend\django_backend"
```

```powershell
py -3.12 -m venv .venv
```

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt pyarrow
```

## Step 3: Train and benchmark

These commands use full paths, so they work from any folder.

Train on the true fraud labels. This shows the best a model can do:

```powershell
& "D:\InsureX Nexus AI\backend\django_backend\.venv\Scripts\python.exe" "D:\InsureX Nexus AI\backend\ml\lumora\train_fraud_model.py" --data "D:\InsureX Nexus AI\backend\data\us\lumora_full" --out "D:\InsureX Nexus AI\backend\ml\lumora\runs\full_truth"
```

Train on investigator outcomes only. This is what a real insurer would have:

```powershell
& "D:\InsureX Nexus AI\backend\django_backend\.venv\Scripts\python.exe" "D:\InsureX Nexus AI\backend\ml\lumora\train_fraud_model.py" --data "D:\InsureX Nexus AI\backend\data\us\lumora_full" --out "D:\InsureX Nexus AI\backend\ml\lumora\runs\full_siu" --label siu
```

Options:

| Option | Default | Meaning |
| --- | --- | --- |
| `--label` | `truth` | `truth` = `ground_truth/truth_claims.is_claim_fraud`; `siu` = confirmed or cleared SIU outcomes only |
| `--capacity` | `0.016` | Share of claims the SIU team can review (1.6%) |
| `--test-share` | `0.25` | Newest 25% of claims held out for testing |

## Step 4: Read the results

The script prints a table like this (from the 50K sample):

```
Test set: 1,840 claims, fraud rate 6.7%
SIU capacity 1.6%  ->  29 claims reviewed
            ROC-AUC  precision   recall  fraud $
Model         0.838      55.2%    12.9%    32.0%
Rules         0.567      17.2%     4.0%    18.7%
```

- **ROC-AUC:** how well the score ranks fraud above genuine claims overall (0.5 = random, 1.0 = perfect).
- **precision / recall / fraud $:** when SIU reviews only the top 1.6% of claims by score, the share of those that are fraud, the share of all fraud caught, and the share of fraud dollars caught.
- **Model vs Rules:** the question is whether the model beats the rules at the same review capacity. On the sample, it does: about 3 times the precision and recall.

Each run folder contains:

| File | What it is |
| --- | --- |
| `report.json` | All the metrics above, plus the top features |
| `feature_importance.csv` | How much each feature contributed |
| `lumora_fraud.joblib` | The trained model (Git ignores `runs/`) |

## How the split and features work

- **Time-based split:** the model trains on older claims and is tested on the newest, as if it had been put into service. This is stricter than a random split.
- **Features** are things known at, or soon after, first notice of loss: days from binding to loss, days to term end, report delay, night loss, police report, listed operator, odometer vs declared miles, loss away from the garaging ZIP or state, prior claims on the customer and vehicle, number of injury coverages and claimants, claimed amount vs MSRP, and attorney within 30 days.
- **Excluded on purpose:** paid, reserve and incurred amounts, claim status, total-loss flag and final attorney status. They're only known after the claim is handled, so using them would leak the answer.

## Rules

- **`ground_truth/` never goes into the app database.** It's only for training and benchmarking here.
- Results are **on synthetic data**. Before a client relies on the score, retrain on their own settled claims and SIU outcomes.
- With `--label siu`, the 50K sample has only about 100 outcomes, which is too few. The full book has 2,390 SIU investigations (728 confirmed fraud, 1,206 cleared), enough to train on.
