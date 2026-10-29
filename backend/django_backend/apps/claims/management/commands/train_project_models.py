import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from scipy.stats import chi2_contingency
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix,
                             f1_score, log_loss, mean_absolute_error, precision_recall_curve,
                             precision_score, r2_score, recall_score, roc_auc_score, roc_curve,
                             root_mean_squared_error)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from lightgbm import LGBMClassifier


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
ORACLE_SCALE_POS_WEIGHT = 3.0
ORACLE_MIN_RECALL = 0.75
ORACLE_MIN_THRESHOLD = 0.05
ORACLE_MAX_THRESHOLD = 0.50
PREVIOUS_ORACLE_THRESHOLD = 0.803338


def build_pipeline(numeric, categorical, estimator, dense_categorical=False):
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scaler", StandardScaler()),
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
        ("one_hot", OneHotEncoder(handle_unknown="ignore", sparse_output=not dense_categorical)),
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


def oracle_classifier():
    """Calibrated LightGBM pipeline with a validation-selected fraud threshold."""
    estimator = LGBMClassifier(
        n_estimators=350, num_leaves=15, learning_rate=0.03,
        min_child_samples=30, reg_lambda=2.0, subsample=0.8,
        colsample_bytree=0.8, scale_pos_weight=ORACLE_SCALE_POS_WEIGHT,
        random_state=42, verbosity=-1, n_jobs=-1,
    )
    pipeline = build_pipeline(
        ORACLE_NUMERIC, ORACLE_CATEGORICAL, estimator,
    )
    return CalibratedClassifierCV(estimator=pipeline, method="sigmoid", cv=3, ensemble=False)


def fit_oracle(model, features, target):
    model.fit(features, target)
    return model


def classifier_metrics(target, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(target, predictions, labels=[0, 1]).ravel()
    return {
        "threshold": round(float(threshold), 6),
        "precision": round(float(precision_score(target, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(target, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(target, predictions, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(target, probabilities)), 4),
        "pr_auc": round(float(average_precision_score(target, probabilities)), 4),
        "log_loss": round(float(log_loss(target, probabilities, labels=[0, 1])), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "alert_rate": round(float(predictions.mean()), 4),
    }


def oracle_data_audit(oracle, insurance):
    target = oracle["FraudFound_P"].astype(int)
    class_counts = {str(key): int(value) for key, value in target.value_counts().sort_index().items()}
    numeric = oracle.select_dtypes(include="number")
    numeric_correlations = numeric.corr(numeric_only=True)["FraudFound_P"].drop("FraudFound_P")
    # Include all numeric columns in the audit (even excluded identifiers) so
    # ID/time redundancy can be spotted and recorded explicitly.
    feature_correlation = numeric.drop(columns=["FraudFound_P"], errors="ignore").corr(numeric_only=True).abs()
    correlated_pairs = []
    columns = list(feature_correlation.columns)
    for index, left in enumerate(columns):
        for right in columns[index + 1:]:
            value = float(feature_correlation.loc[left, right])
            if value >= 0.8:
                correlated_pairs.append({"features": [left, right], "absolute_correlation": round(value, 4)})

    categorical_associations = []
    for feature in ORACLE_CATEGORICAL:
        table = pd.crosstab(oracle[feature], target)
        if min(table.shape) < 2:
            continue
        chi_square = chi2_contingency(table, correction=False)[0]
        denominator = int(table.to_numpy().sum()) * (min(table.shape) - 1)
        categorical_associations.append({
            "feature": feature,
            "cramers_v": round(float(np.sqrt(chi_square / denominator)), 4),
        })
    categorical_associations.sort(key=lambda item: item["cramers_v"], reverse=True)

    severity_counts = insurance["incident_severity"].value_counts(dropna=False)
    total_loss = insurance["incident_severity"].astype(str).str.strip().str.casefold().eq("total loss")
    fraud_label = insurance["fraud_reported"].astype(str).str.strip().str.upper().eq("Y")
    total_loss_fraud = {}
    for label, mask in (("total_loss", total_loss), ("other_severity", ~total_loss)):
        count = int(mask.sum())
        fraud_count = int((mask & fraud_label).sum())
        total_loss_fraud[label] = {
            "rows": count,
            "fraud_rows": fraud_count,
            "fraud_rate": round(fraud_count / count, 4) if count else None,
        }

    return {
        "fraud_oracle": {
            "rows": int(len(oracle)),
            "fraud_rows": int(target.sum()),
            "non_fraud_rows": int((target == 0).sum()),
            "fraud_rate": round(float(target.mean()), 4),
            "class_imbalance_ratio_nonfraud_to_fraud": round(class_counts.get("0", 0) / max(class_counts.get("1", 0), 1), 2),
            "missing_cells": int(oracle.isna().sum().sum()),
            "duplicate_rows": int(oracle.duplicated().sum()),
            "preprocessing": {
                "numeric": "median imputation followed by standard scaling",
                "categorical": "most-frequent imputation followed by one-hot encoding; unknown categories ignored",
            },
            "target_counts": class_counts,
            "top_numeric_target_correlations": [
                {"feature": name, "correlation": round(float(value), 4)}
                for name, value in numeric_correlations.abs().sort_values(ascending=False).head(10).items()
            ],
            "numeric_feature_correlations_at_least_0_8": correlated_pairs,
            "top_categorical_target_associations": categorical_associations[:8],
            "excluded_identifier_columns": ["PolicyNumber", "RepNumber"],
            "feature_timing_caveat": (
                "Fault, NumberOfSuppliments, Days_Policy_Claim, PoliceReportFiled, and WitnessPresent "
                "may be known only after initial claim intake. Confirm their availability at the intended "
                "scoring time before production use; this CSV has no field-timing documentation."
            ),
            "total_loss_label": "Fraud Oracle has no explicit total-loss outcome column.",
        },
        "insurance_total_loss_audit": {
            "severity_counts": {str(key): int(value) for key, value in severity_counts.items()},
            "label_definition": "incident_severity equals Total Loss (proxy label; not independently verified as an insurer total-loss outcome).",
            "fraud_by_severity": total_loss_fraud,
        },
    }


def evaluate_oracle(oracle, oracle_x, oracle_y, models_dir):
    X_development, X_test, y_development, y_test = train_test_split(
        oracle_x, oracle_y, test_size=0.2, random_state=42, stratify=oracle_y,
    )
    X_train, X_validation, y_train, y_validation = train_test_split(
        X_development, y_development, test_size=0.25, random_state=43,
        stratify=y_development,
    )

    # Reproduce the previous RF operating point on the same untouched test split.
    previous_model = classifier(ORACLE_NUMERIC, ORACLE_CATEGORICAL)
    previous_model.fit(X_train, y_train)
    previous_test_probabilities = previous_model.predict_proba(X_test)[:, list(previous_model.classes_).index(1)]
    previous_metrics = classifier_metrics(y_test, previous_test_probabilities, PREVIOUS_ORACLE_THRESHOLD)

    # Choose a threshold only from validation predictions. The test partition is not used for selection.
    selection_model = fit_oracle(oracle_classifier(), X_train, y_train)
    validation_probabilities = selection_model.predict_proba(X_validation)[:, list(selection_model.classes_).index(1)]
    threshold_sweep = []
    for threshold in np.round(np.arange(ORACLE_MIN_THRESHOLD, ORACLE_MAX_THRESHOLD + 0.001, 0.01), 2):
        threshold_sweep.append({"threshold": float(threshold), **classifier_metrics(y_validation, validation_probabilities, threshold)})
    eligible = [
        row for row in threshold_sweep
        if row["recall"] >= ORACLE_MIN_RECALL and row["precision"] > float(oracle_y.mean())
    ]
    if not eligible:
        raise CommandError(
            "No validation threshold from 0.05 to 0.50 achieved at least 75% recall and precision above the dataset fraud rate."
        )
    selected = max(eligible, key=lambda row: (row["precision"], row["f1"], row["threshold"]))
    selected_threshold = float(selected["threshold"])

    # Evaluate with all development rows, then refit on all rows for the shipped artifact.
    evaluation_model = fit_oracle(oracle_classifier(), X_development, y_development)
    test_probabilities = evaluation_model.predict_proba(X_test)[:, list(evaluation_model.classes_).index(1)]
    tuned_metrics = classifier_metrics(y_test, test_probabilities, selected_threshold)
    default_metrics = classifier_metrics(y_test, test_probabilities, 0.5)
    final_model = fit_oracle(oracle_classifier(), oracle_x, oracle_y)

    models_dir.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(2, 2, figsize=(12, 9))
    previous_precision, previous_recall, _ = precision_recall_curve(y_test, previous_test_probabilities)
    tuned_precision, tuned_recall, _ = precision_recall_curve(y_test, test_probabilities)
    axes[0, 0].plot(previous_recall, previous_precision, label=f"Previous RF (AP={previous_metrics['pr_auc']:.3f})")
    axes[0, 0].plot(tuned_recall, tuned_precision, label=f"Tuned model (AP={tuned_metrics['pr_auc']:.3f})")
    axes[0, 0].set(title="Precision–Recall curve (test set)", xlabel="Recall", ylabel="Precision", xlim=(0, 1), ylim=(0, 1))
    axes[0, 0].legend(loc="best")
    previous_fpr, previous_tpr, _ = roc_curve(y_test, previous_test_probabilities)
    tuned_fpr, tuned_tpr, _ = roc_curve(y_test, test_probabilities)
    axes[0, 1].plot(previous_fpr, previous_tpr, label=f"Previous RF (AUC={previous_metrics['roc_auc']:.3f})")
    axes[0, 1].plot(tuned_fpr, tuned_tpr, label=f"Tuned model (AUC={tuned_metrics['roc_auc']:.3f})")
    axes[0, 1].plot([0, 1], [0, 1], linestyle="--", color="gray")
    axes[0, 1].set(title="ROC curve (test set)", xlabel="False-positive rate", ylabel="True-positive rate", xlim=(0, 1), ylim=(0, 1))
    axes[0, 1].legend(loc="best")
    for axis, title, probabilities, threshold in (
        (axes[1, 0], f"Previous RF @ {PREVIOUS_ORACLE_THRESHOLD:.3f}", previous_test_probabilities, PREVIOUS_ORACLE_THRESHOLD),
        (axes[1, 1], f"Tuned model @ {selected_threshold:.2f}", test_probabilities, selected_threshold),
    ):
        matrix = confusion_matrix(y_test, probabilities >= threshold, labels=[0, 1])
        image = axis.imshow(matrix, cmap="Blues")
        axis.set(title=title, xlabel="Predicted label", ylabel="Actual label", xticks=[0, 1], yticks=[0, 1], xticklabels=["Not fraud", "Fraud"], yticklabels=["Not fraud", "Fraud"])
        for (row, column), value in np.ndenumerate(matrix):
            axis.text(column, row, str(value), ha="center", va="center", color="black")
    figure.tight_layout()
    chart_path = models_dir / "fraud_oracle_evaluation.png"
    figure.savefig(chart_path, dpi=160, bbox_inches="tight")
    plt.close(figure)

    return final_model, {
        "model": "fraud_oracle_fraud",
        **tuned_metrics,
        "calibration": "sigmoid (3-fold cross-validation)",
        "imbalance_strategy": {"method": "LightGBM scale_pos_weight", "value": ORACLE_SCALE_POS_WEIGHT},
        "threshold_selection": {
            "validation_recall_target": ORACLE_MIN_RECALL,
            "precision_must_exceed_dataset_fraud_rate": True,
            "threshold_range": [ORACLE_MIN_THRESHOLD, ORACLE_MAX_THRESHOLD],
            "selected_validation_metrics": selected,
            "validation_sweep": threshold_sweep,
        },
        "previous_pipeline_test_metrics": previous_metrics,
        "tuned_model_default_threshold_test_metrics": default_metrics,
        "test_rows": int(len(y_test)),
        "test_fraud_rows": int(y_test.sum()),
        "test_non_fraud_rows": int((y_test == 0).sum()),
        "threshold_source": "selected on validation split; test split used once for final metrics",
        "evaluation_chart": str(chart_path.name),
    }


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
        parser.add_argument("--insurance-file", type=Path, default=backend_dir / "data" / "insurance_claims.csv")
        parser.add_argument("--fraud-file", type=Path, default=backend_dir / "data" / "fraud_oracle.csv")
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
        models_dir = options["models_dir"]
        models_dir.mkdir(parents=True, exist_ok=True)
        oracle_model, oracle_metrics = evaluate_oracle(oracle, oracle_X, oracle_y, models_dir)
        data_audit = oracle_data_audit(oracle, insurance)
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
                "total_loss": "incident_severity equals Total Loss (proxy; see data audit)",
                "insurance_fraud": "fraud_reported equals Y",
                "fraud_oracle_fraud": "FraudFound_P equals 1",
            },
            "data_audit": data_audit,
            "decision_thresholds": {
                "insurance_fraud": fraud_metrics["decision_threshold"],
                "fraud_oracle_fraud": oracle_metrics["threshold"],
            },
            "metrics": [fraud_metrics, cost_metrics, total_loss_metrics, oracle_metrics],
            "fraud_oracle_comparison": {
                "previous_pipeline": oracle_metrics["previous_pipeline_test_metrics"],
                "tuned_pipeline": {key: oracle_metrics[key] for key in (
                    "threshold", "precision", "recall", "f1", "roc_auc", "pr_auc",
                    "log_loss", "confusion_matrix", "alert_rate",
                )},
            },
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
            display_keys = (
                "threshold", "precision", "recall", "f1", "roc_auc", "pr_auc",
                "log_loss", "confusion_matrix", "alert_rate", "imbalance_strategy",
            )
            summary = {key: metric[key] for key in display_keys if key in metric}
            if metric["model"] != "fraud_oracle_fraud":
                summary = {key: value for key, value in metric.items() if key != "model"}
            self.stdout.write(self.style.SUCCESS(f"{metric['model']}: {json.dumps(summary)}"))
        before = oracle_metrics["previous_pipeline_test_metrics"]
        after = oracle_metrics
        self.stdout.write("\nFraud Oracle held-out test comparison (same split):")
        self.stdout.write("Pipeline                 Recall  Precision  F1      ROC-AUC  PR-AUC  Log loss")
        self.stdout.write(
            f"Previous RF @ {PREVIOUS_ORACLE_THRESHOLD:.3f}     "
            f"{before['recall']:.4f}  {before['precision']:.4f}     {before['f1']:.4f}  "
            f"{before['roc_auc']:.4f}   {before['pr_auc']:.4f}  {before['log_loss']:.4f}"
        )
        self.stdout.write(
            f"Tuned model @ {after['threshold']:.2f}       "
            f"{after['recall']:.4f}  {after['precision']:.4f}     {after['f1']:.4f}  "
            f"{after['roc_auc']:.4f}   {after['pr_auc']:.4f}  {after['log_loss']:.4f}"
        )
        self.stdout.write(f"Confusion matrix before: {json.dumps(before['confusion_matrix'])}")
        self.stdout.write(f"Confusion matrix after:  {json.dumps(after['confusion_matrix'])}")
        self.stdout.write(f"Evaluation plots: {models_dir / oracle_metrics['evaluation_chart']}")
        self.stdout.write(self.style.SUCCESS(f"Saved {len(artifacts)} models and the training report to {models_dir}"))
