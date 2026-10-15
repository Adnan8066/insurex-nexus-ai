import os

import joblib
import pandas as pd
from django.conf import settings


ML_DIR = os.path.join(settings.BASE_DIR.parent, "ml")
MODELS_DIR = os.path.join(ML_DIR, "models")
_MODEL_FILES = {
    "repair_cost": "repair_cost.joblib",
    "fraud_risk": "fraud_risk.joblib",
    "total_loss": "total_loss.joblib",
    "fraud_oracle_fraud": "fraud_oracle_fraud.joblib",
}
_models = {name: None for name in _MODEL_FILES}
_model_mtimes = {}
_model_load_errors = {}


class MLModelUnavailable(RuntimeError):
    """Raised when a trained model cannot produce a prediction for this input."""

_INSURANCE_FEATURES = [
    "age", "policy_deductable", "policy_annual_premium", "incident_type",
    "incident_severity", "number_of_vehicles_involved", "property_damage",
    "bodily_injuries", "witnesses", "police_report_available", "auto_make",
    "auto_model", "auto_year",
]
_ORACLE_FEATURES = [
    "Month", "WeekOfMonth", "DayOfWeek", "Make", "AccidentArea",
    "DayOfWeekClaimed", "MonthClaimed", "WeekOfMonthClaimed", "Sex",
    "MaritalStatus", "Age", "Fault", "PolicyType", "VehicleCategory",
    "VehiclePrice", "Deductible", "DriverRating", "Days_Policy_Accident",
    "Days_Policy_Claim", "PastNumberOfClaims", "AgeOfVehicle",
    "AgeOfPolicyHolder", "PoliceReportFiled", "WitnessPresent", "AgentType",
    "NumberOfSuppliments", "AddressChange_Claim", "NumberOfCars", "Year",
    "BasePolicy",
]


def load_models():
    """Load artifacts lazily and reload them after a new training run."""
    for name, filename in _MODEL_FILES.items():
        path = os.path.join(MODELS_DIR, filename)
        try:
            modified = os.stat(path).st_mtime_ns
        except FileNotFoundError:
            _models[name] = None
            _model_mtimes.pop(name, None)
            _model_load_errors.pop(name, None)
            continue
        except PermissionError:
            _models[name] = None
            _model_mtimes.pop(name, None)
            _model_load_errors[name] = f"The backend cannot read the trained model file '{filename}'. Grant the backend process read access to the model artifacts."
            continue
        if _model_mtimes.get(name) != modified:
            try:
                _models[name] = _configure_inference_model(joblib.load(path))
                _model_mtimes[name] = modified
                _model_load_errors.pop(name, None)
            except PermissionError:
                _models[name] = None
                _model_mtimes.pop(name, None)
                _model_load_errors[name] = f"The backend cannot read the trained model file '{filename}'. Grant the backend process read access to the model artifacts."
    return _models


def _unavailable_model_message(name, default_message):
    return _model_load_errors.get(name, default_message)


def _configure_inference_model(model):
    """Avoid joblib worker-pipe creation in restricted Windows environments."""
    if hasattr(model, "get_params") and hasattr(model, "set_params"):
        single_threaded = {
            name: 1
            for name, value in model.get_params(deep=True).items()
            if name.endswith("n_jobs") and value not in (None, 1)
        }
        if single_threaded:
            model.set_params(**single_threaded)
    return model


def _input_frame(claim_data, feature_names):
    return pd.DataFrame([{name: claim_data.get(name) for name in feature_names}], columns=feature_names)


def _fraud_probability(model, frame):
    probabilities = model.predict_proba(frame)[0]
    classes = list(model.classes_)
    positive_index = classes.index(1) if 1 in classes else classes.index("1")
    return float(probabilities[positive_index])


def _fraud_result(score, decision_threshold=70):
    score = round(score, 2)
    medium_threshold = min(40.0, decision_threshold * 0.5)
    if score >= decision_threshold:
        level, factors = "high", ["model identified a high-risk pattern", "recommend investigation"]
    elif score >= medium_threshold:
        level, factors = "medium", ["model identified a moderate-risk pattern", "enhanced review recommended"]
    else:
        level, factors = "low", ["model identified a low-risk pattern"]
    return {
        "score": score,
        "level": level,
        "factors": factors,
        "behavioral": [],
        "network": {"connected_claims": 0, "shared_parties": []},
    }


def predict_repair_cost_ml(claim_data):
    """Predict vehicle repair cost with the model trained on insurance claims."""
    model = load_models()["repair_cost"]
    if claim_data.get("_source_dataset") == "fraud_oracle":
        raise MLModelUnavailable("Repair-cost predictions are not supported for Fraud Oracle records; that dataset has no repair-cost labels.")
    if model is None:
        raise MLModelUnavailable(_unavailable_model_message("repair_cost", "The trained repair-cost model is not available. Train the project models before assessing this claim."))
    try:
        prediction = max(0.0, float(model.predict(_input_frame(claim_data, _INSURANCE_FEATURES))[0]))
        return {
            "cost": round(prediction, 2),
            "breakdown": {},
            "time_estimate": None,
            "comparable_count": None,
        }
    except (ValueError, TypeError, KeyError) as exc:
        raise MLModelUnavailable(f"The repair-cost model could not score this claim: {exc}") from exc


def detect_fraud_ml(claim_data):
    """Score fraud with the model trained for the source dataset's feature schema."""
    models = load_models()
    oracle = claim_data.get("_source_dataset") == "fraud_oracle"
    model = models["fraud_oracle_fraud"] if oracle else models["fraud_risk"]
    if model is None:
        model_name = "fraud_oracle_fraud" if oracle else "fraud_risk"
        raise MLModelUnavailable(_unavailable_model_message(model_name, "The trained fraud model for this claim type is not available. Train the project models before assessing this claim."))
    features = _ORACLE_FEATURES if oracle else _INSURANCE_FEATURES
    try:
        score = _fraud_probability(model, _input_frame(claim_data, features)) * 100
        threshold = 70
        if oracle:
            report_path = os.path.join(MODELS_DIR, "training_report.json")
            try:
                import json
                with open(report_path, encoding="utf-8") as report_file:
                    threshold = float(json.load(report_file)["decision_thresholds"]["fraud_oracle_fraud"]) * 100
            except (OSError, ValueError, KeyError, TypeError):
                pass
        return _fraud_result(score, threshold)
    except (ValueError, TypeError, KeyError) as exc:
        raise MLModelUnavailable(f"The fraud model could not score this claim: {exc}") from exc


def predict_total_loss_ml(claim_data):
    """Estimate total-loss probability from the insurance claims model."""
    model = load_models()["total_loss"]
    if claim_data.get("_source_dataset") == "fraud_oracle":
        raise MLModelUnavailable("Total-loss prediction is not supported for Fraud Oracle records; that dataset has no total-loss outcome label.")
    if model is None:
        raise MLModelUnavailable(_unavailable_model_message("total_loss", "The trained total-loss model is not available. Train the project models before assessing this claim."))
    try:
        probability = _fraud_probability(model, _input_frame(claim_data, _INSURANCE_FEATURES)) * 100
        return {"probability": round(min(max(probability, 0), 100), 2)}
    except (ValueError, TypeError, KeyError) as exc:
        raise MLModelUnavailable(f"The total-loss model could not score this claim: {exc}") from exc


def get_model_status():
    models = load_models()
    report_path = os.path.join(MODELS_DIR, "training_report.json")
    report = None
    if os.path.exists(report_path):
        try:
            import json
            with open(report_path, encoding="utf-8") as report_file:
                report = json.load(report_file)
        except (OSError, ValueError):
            report = None
    return {
        "repair_cost_model": models["repair_cost"] is not None,
        "fraud_risk_model": models["fraud_risk"] is not None,
        "fraud_oracle_model": models["fraud_oracle_fraud"] is not None,
        "total_loss_model": models["total_loss"] is not None,
        "model_load_errors": dict(_model_load_errors),
        "training_report": report,
    }
