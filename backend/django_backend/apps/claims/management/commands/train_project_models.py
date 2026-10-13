import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, f1_score, mean_absolute_error,
                             precision_score, r2_score, recall_score, roc_auc_score,
                             precision_recall_curve, root_mean_squared_error)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


INSURANCE_FEATURES = [
    "age", "policy_deductable", "policy_annual_premium", "incident_type",
    "incident_severity", "number_of_vehicles_involved", "property_damage",
    "bodily_injuries", "witnesses", "police_report_available", "auto_make",
    "auto_model", "auto_year",
]
INSURANCE_NUMERIC = [
    "age", "policy_deductable", "policy_annual_premium",
    "number_of_vehicles_involved", "bodily_injuries", "witnesses", "auto_year",
]
INSURANCE_CATEGORICAL = [name for name in INSURANCE_FEATURES if name not in INSURANCE_NUMERIC]

ORACLE_FEATURES = [
    "Month", "WeekOfMonth", "DayOfWeek", "Make", "AccidentArea",
    "DayOfWeekClaimed", "MonthClaimed", "WeekOfMonthClaimed", "Sex",
    "MaritalStatus", "Age", "Fault", "PolicyType", "VehicleCategory",
    "VehiclePrice", "Deductible", "DriverRating", "Days_Policy_Accident",
    "Days_Policy_Claim", "PastNumberOfClaims", "AgeOfVehicle",
    "AgeOfPolicyHolder", "PoliceReportFiled", "WitnessPresent", "AgentType",
    "NumberOfSuppliments", "AddressChange_Claim", "NumberOfCars", "Year",
    "BasePolicy",
]
ORACLE_NUMERIC = ["WeekOfMonth", "WeekOfMonthClaimed", "Age", "Deductible", "DriverRating", "Year"]
ORACLE_CATEGORICAL = [name for name in ORACLE_FEATURES if name not in ORACLE_NUMERIC]


def build_pipeline(numeric, categorical, estimator):
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scaler", StandardScaler()),
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
        ("one_hot", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessing = ColumnTransformer([
        ("numeric", numeric_pipeline, numeric),
        ("categorical", categorical_pipeline, categorical),
    ])
    return Pipeline([("preprocessing", preprocessing), ("estimator", estimator)])


def classifier(numeric, categorical):
    model = RandomForestClassifier(
        n_estimators=250, max_depth=12, min_samples_leaf=4,
        class_weight="balanced_subsample", random_state=42, n_jobs=-1,
    )
    return build_pipeline(numeric, categorical, model)


def regressor(numeric, categorical):
    model = RandomForestRegressor(
        n_estimators=250, max_depth=12, min_samples_leaf=4,
        random_state=42, n_jobs=-1,
    )
    return build_pipeline(numeric, categorical, model)


def evaluate_classifier(template, X, y, name, minimum_precision=None):
    X_development, X_test, y_development, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )
    threshold = 0.5
    calibration_rows = 0
    if minimum_precision is not None:
        X_train, X_calibration, y_train, y_calibration = train_test_split(
            X_development, y_development, test_size=0.25, random_state=43,
            stratify=y_development,
        )
        model = template()
        model.fit(X_train, y_train)
        calibration_probabilities = model.predict_proba(X_calibration)[:, list(model.classes_).index(1)]
        precision_values, recall_values, thresholds = precision_recall_curve(y_calibration, calibration_probabilities)
        eligible = np.flatnonzero(precision_values[:-1] >= minimum_precision)
        if not len(eligible):
            raise CommandError(
                f"Could not reach {minimum_precision:.0%} precision for {name} on the calibration split."
            )
        best = eligible[np.argmax(recall_values[eligible])]
        threshold = float(thresholds[best])
        calibration_rows = int(len(y_calibration))
    else:
        X_train, y_train = X_development, y_development

    model = template()
    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_test)[:, list(model.classes_).index(1)]
    predictions = (probabilities >= threshold).astype(int)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, predictions, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        "decision_threshold": round(threshold, 6),
        "holdout_rows": int(len(y_test)),
        "calibration_rows": calibration_rows,
        "class_counts": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
    }
    fitted = template()
    fitted.fit(X, y)
    return fitted, {"model": name, **metrics}


def evaluate_regressor(template, X, y, name):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42,
    )
    model = template()
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    metrics = {
        "mae": round(float(mean_absolute_error(y_test, predictions)), 2),
        "rmse": round(float(root_mean_squared_error(y_test, predictions)), 2),
        "r2": round(float(r2_score(y_test, predictions)), 4),
        "holdout_rows": int(len(y_test)),
    }
    fitted = template()
    fitted.fit(X, y)
    return fitted, {"model": name, **metrics}


class Command(BaseCommand):
    help = "Train app models on the bundled insurance and Fraud Oracle datasets."

    def add_arguments(self, parser):
        backend_dir = settings.BASE_DIR.parent
        parser.add_argument("--insurance-file", type=Path, default=backend_dir / "insurance_claims.csv")
        parser.add_argument("--fraud-file", type=Path, default=backend_dir / "fraud_oracle.csv")
        parser.add_argument("--models-dir", type=Path, default=backend_dir / "ml" / "models")

    def handle(self, *args, **options):
        insurance_path = options["insurance_file"]
        oracle_path = options["fraud_file"]
        for path in (insurance_path, oracle_path):
            if not path.is_file():
                raise CommandError(f"Dataset not found: {path}")

        insurance = pd.read_csv(insurance_path)
        oracle = pd.read_csv(oracle_path, encoding="utf-8-sig")
        if insurance.empty or oracle.empty:
            raise CommandError("Both training datasets must contain records.")
        if not set(INSURANCE_FEATURES + ["fraud_reported", "vehicle_claim", "total_claim_amount"]).issubset(insurance.columns):
            raise CommandError("Insurance dataset is missing one or more required training columns.")
        if not set(ORACLE_FEATURES + ["FraudFound_P"]).issubset(oracle.columns):
            raise CommandError("Fraud Oracle dataset is missing one or more required training columns.")

        insurance_X = insurance[INSURANCE_FEATURES].copy()
        insurance_y = insurance["fraud_reported"].astype(str).str.strip().str.upper().map({"Y": 1, "N": 0})
        if insurance_y.isna().any() or insurance_y.nunique() != 2:
            raise CommandError("Insurance fraud_reported must contain both Y and N labels.")

        fraud_model, fraud_metrics = evaluate_classifier(
            lambda: classifier(INSURANCE_NUMERIC, INSURANCE_CATEGORICAL),
            insurance_X, insurance_y.astype(int), "insurance_fraud",
        )

        cost_y = pd.to_numeric(insurance["vehicle_claim"], errors="coerce")
        cost_valid = cost_y.notna()
        cost_model, cost_metrics = evaluate_regressor(
            lambda: regressor(INSURANCE_NUMERIC, INSURANCE_CATEGORICAL),
            insurance_X.loc[cost_valid], cost_y.loc[cost_valid], "repair_cost",
        )

        total_loss_y = insurance["incident_severity"].astype(str).str.strip().str.lower().eq("total loss").astype(int)
        if total_loss_y.nunique() != 2:
            raise CommandError("The insurance data does not contain both total-loss classes.")
        total_loss_features = [name for name in INSURANCE_FEATURES if name != "incident_severity"]
        total_loss_categorical = [name for name in INSURANCE_CATEGORICAL if name != "incident_severity"]
        total_loss_model, total_loss_metrics = evaluate_classifier(
            lambda: classifier(INSURANCE_NUMERIC, total_loss_categorical),
            insurance_X[total_loss_features], total_loss_y, "total_loss",
        )

        oracle_X = oracle[ORACLE_FEATURES].copy()
        oracle_y = pd.to_numeric(oracle["FraudFound_P"], errors="coerce")
        valid = oracle_y.notna()
        oracle_X, oracle_y = oracle_X.loc[valid], oracle_y.loc[valid].astype(int)
        if oracle_y.nunique() != 2:
            raise CommandError("Fraud Oracle FraudFound_P must contain both 0 and 1 labels.")
        oracle_model, oracle_metrics = evaluate_classifier(
            lambda: classifier(ORACLE_NUMERIC, ORACLE_CATEGORICAL),
        oracle_X, oracle_y, "fraud_oracle_fraud",
        minimum_precision=0.9,
        )

        models_dir = options["models_dir"]
        models_dir.mkdir(parents=True, exist_ok=True)
        artifacts = {
            "fraud_risk.joblib": fraud_model,
            "repair_cost.joblib": cost_model,
            "total_loss.joblib": total_loss_model,
            "fraud_oracle_fraud.joblib": oracle_model,
        }
        report = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "datasets": {
                "insurance_claims": {"file": insurance_path.name, "rows": len(insurance)},
                "fraud_oracle": {"file": oracle_path.name, "rows": len(oracle)},
            },
            "targets": {
                "repair_cost": "vehicle_claim",
                "total_loss": "incident_severity equals Total Loss",
                "insurance_fraud": "fraud_reported equals Y",
                "fraud_oracle_fraud": "FraudFound_P equals 1",
            },
            "decision_thresholds": {
                "insurance_fraud": fraud_metrics["decision_threshold"],
                "fraud_oracle_fraud": oracle_metrics["decision_threshold"],
            },
            "metrics": [fraud_metrics, cost_metrics, total_loss_metrics, oracle_metrics],
        }

        staged = []
        try:
            with tempfile.TemporaryDirectory(prefix="training-", dir=models_dir) as temp_dir:
                for filename, model in artifacts.items():
                    staged_path = Path(temp_dir) / filename
                    joblib.dump(model, staged_path)
                    staged.append((staged_path, models_dir / filename))
                report_path = Path(temp_dir) / "training_report.json"
                report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                staged.append((report_path, models_dir / "training_report.json"))
                for staged_path, destination in staged:
                    os.replace(staged_path, destination)
        except Exception as exc:
            raise CommandError(f"Could not save trained artifacts: {exc}") from exc

        for metric in report["metrics"]:
            self.stdout.write(self.style.SUCCESS(f"{metric['model']}: {json.dumps({k: v for k, v in metric.items() if k != 'model'})}"))
        self.stdout.write(self.style.SUCCESS(f"Saved {len(artifacts)} models and the training report to {models_dir}"))
