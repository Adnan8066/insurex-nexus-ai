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
            continue
        if _model_mtimes.get(name) != modified:
            _models[name] = joblib.load(path)
            _model_mtimes[name] = modified
    return _models


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


def _fallback_repair_cost(claim_data):
    amount = float(claim_data.get("claim_amount") or claim_data.get("total_claim_amount") or 0)
    cost = round(amount * 0.85, 2)
    return {
        "cost": cost,
        "breakdown": {
            "labor": round(cost * 0.4, 2), "parts": round(cost * 0.35, 2),
            "materials": round(cost * 0.1, 2), "overhead": round(cost * 0.05, 2),
        },
        "time_estimate": 5,
        "comparable_count": 12,
    }


def predict_repair_cost_ml(claim_data):
    """Predict vehicle repair cost with the model trained on insurance claims."""
    model = load_models()["repair_cost"]
    if model is None or claim_data.get("_source_dataset") == "fraud_oracle":
        return _fallback_repair_cost(claim_data)
    try:
        prediction = max(0.0, float(model.predict(_input_frame(claim_data, _INSURANCE_FEATURES))[0]))
        return {
            "cost": round(prediction, 2),
            "breakdown": {
                "labor": round(prediction * 0.4, 2), "parts": round(prediction * 0.35, 2),
                "materials": round(prediction * 0.1, 2), "overhead": round(prediction * 0.05, 2),
            },
            "time_estimate": 5,
            "comparable_count": 1000,
        }
    except (ValueError, TypeError, KeyError):
        return _fallback_repair_cost(claim_data)


def detect_fraud_ml(claim_data):
    """Score fraud with the model trained for the source dataset's feature schema."""
    models = load_models()
    oracle = claim_data.get("_source_dataset") == "fraud_oracle"
    model = models["fraud_oracle_fraud"] if oracle else models["fraud_risk"]
    if model is None:
        return _fraud_result(15.0)
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
    except (ValueError, TypeError, KeyError):
        return _fraud_result(15.0)


def predict_total_loss_ml(claim_data):
    """Estimate total-loss probability from the insurance claims model."""
    model = load_models()["total_loss"]
    if model is None or claim_data.get("_source_dataset") == "fraud_oracle":
        return {"probability": 10.0}
    try:
        probability = _fraud_probability(model, _input_frame(claim_data, _INSURANCE_FEATURES)) * 100
        return {"probability": round(min(max(probability, 0), 100), 2)}
    except (ValueError, TypeError, KeyError):
        return {"probability": 10.0}


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
        "training_report": report,
    }
