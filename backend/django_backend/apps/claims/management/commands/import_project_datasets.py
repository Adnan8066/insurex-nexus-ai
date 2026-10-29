import csv
import hashlib
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.claims.models import Claim, ClaimPriority, ClaimStatus, IncidentSeverity, IncidentType
from apps.customers.models import Customer
from apps.policies.models import Policy, PolicyStatus, PolicyType
from apps.vehicles.models import Vehicle


PROJECT_BACKEND = settings.BASE_DIR.parent
INSURANCE_CSV = PROJECT_BACKEND / "data" / "insurance_claims.csv"
FRAUD_CSV = PROJECT_BACKEND / "data" / "fraud_oracle.csv"


def truthy(value):
    return str(value).strip().lower() in {"yes", "y", "true", "1"}


def parse_date(value, field):
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"Invalid {field}: {value!r}") from exc


def decimal_value(value, default="0"):
    try:
        return Decimal(str(value).strip() or default)
    except (InvalidOperation, ValueError):
        return Decimal(default)


def make_vin(source, policy_number):
    digest = hashlib.sha256(f"{source}:{policy_number}".encode()).hexdigest()[:12].upper()
    return f"DX{digest}000"


def month_date(month, year, week=3):
    try:
        month_number = datetime.strptime(month[:3].title(), "%b").month
    except (ValueError, TypeError):
        month_number = 1
    return date(int(year), month_number, min(28, max(1, 1 + (int(week) - 1) * 7)))


def valid_choice(value, choices, fallback):
    return value if value in choices else fallback


class Command(BaseCommand):
    help = "Import the bundled insurance and Fraud Oracle datasets into claims, policies, vehicles, and customers."

    def add_arguments(self, parser):
        parser.add_argument("--insurance-file", type=Path, default=INSURANCE_CSV)
        parser.add_argument("--fraud-file", type=Path, default=FRAUD_CSV)
        parser.add_argument("--skip-insurance", action="store_true")
        parser.add_argument("--skip-fraud", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        insurance_file = options["insurance_file"]
        fraud_file = options["fraud_file"]
        datasets = []
        if not options["skip_insurance"]:
            datasets.append(("insurance", insurance_file))
        if not options["skip_fraud"]:
            datasets.append(("fraud", fraud_file))

        for name, path in datasets:
            if not path.is_file():
                raise CommandError(f"{name} dataset not found: {path}")

        if options["dry_run"]:
            for name, path in datasets:
                with path.open(newline="", encoding="utf-8-sig") as handle:
                    reader = csv.DictReader(handle)
                    rows = list(reader)
                required = {"insurance": {"policy_number", "incident_date", "fraud_reported"},
                            "fraud": {"PolicyNumber", "Month", "Year", "FraudFound_P"}}[name]
                missing = required - set(reader.fieldnames or [])
                if missing:
                    raise CommandError(f"{path.name} is missing required columns: {', '.join(sorted(missing))}")
                self.stdout.write(f"{path.name}: {len(rows)} rows, columns validated")
            return

        with transaction.atomic():
            for name, path in datasets:
                with path.open(newline="", encoding="utf-8-sig") as handle:
                    reader = csv.DictReader(handle)
                    if not reader.fieldnames:
                        raise CommandError(f"{path.name} has no header row")
                    rows = list(reader)
                required = {"insurance": {"policy_number", "incident_date", "fraud_reported"},
                            "fraud": {"PolicyNumber", "Month", "Year", "FraudFound_P"}}[name]
                missing = required - set(reader.fieldnames)
                if missing:
                    raise CommandError(f"{path.name} is missing required columns: {', '.join(sorted(missing))}")

                imported = 0
                for row in rows:
                    if not any((value or "").strip() for value in row.values()):
                        continue
                    if name == "insurance":
                        self.import_insurance_row(row)
                    else:
                        self.import_fraud_row(row)
                    imported += 1
                self.stdout.write(self.style.SUCCESS(f"Imported {imported} {name} dataset claims from {path.name}"))

    def import_related(self, *, source, source_id, policy_number, incident_date, state, premium,
                       deductible, make, model, year, age, raw_data):
        key = f"{source}-{source_id}"
        user, _ = User.objects.update_or_create(
            email=f"{key}@dataset.invalid",
            defaults={"username": key, "first_name": "Dataset", "last_name": f"Record {source_id}",
                      "role": "customer", "is_active": False},
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        Customer.objects.update_or_create(
            user=user,
            defaults={"customer_number": key.upper()[:20],
                      "date_of_birth": date(incident_date.year - min(max(int(age or 35), 18), 100), 1, 1),
                      "license_state": state[:2].upper(), "risk_rating": "dataset", "notes": "Imported sample dataset record."},
        )

        policy_key = f"{source.upper()}-{policy_number}"[:20]
        start_date = incident_date - timedelta(days=365)
        policy, _ = Policy.objects.update_or_create(
            policy_number=policy_key,
            defaults={"customer": user, "type": PolicyType.AUTO_COMPREHENSIVE,
                      "status": PolicyStatus.EXPIRED, "start_date": start_date,
                      "end_date": incident_date + timedelta(days=365), "premium": max(premium, Decimal("0.01")),
                      "deductible": max(deductible, Decimal("0.00")), "auto_renew": False,
                      "coverage": {"source_dataset": source, "source_policy_number": str(policy_number)}},
        )
        vin = make_vin(source, policy_number)
        vehicle, _ = Vehicle.objects.update_or_create(
            vin=vin,
            defaults={"customer": user, "policy": policy, "make": make[:50] or "Unknown",
                      "model": model[:50] or "Unknown", "year": min(max(int(year or incident_date.year), 1900), incident_date.year),
                      "color": "Not provided", "license_plate": f"{source[:2].upper()}{source_id}"[:20],
                      "license_state": state[:2].upper() or "NA", "status": "inactive"},
        )
        return user, policy, vehicle

    def import_insurance_row(self, row):
        policy_number = str(row["policy_number"]).strip()
        claim_key = f"INS-{policy_number}"[:20]
        incident_date = parse_date(row["incident_date"], "incident_date")
        state = row.get("incident_state") or row.get("policy_state") or "NA"
        age = int(float(row.get("age") or 35))
        make, model = row.get("auto_make", "Unknown"), row.get("auto_model", "Unknown")
        premium = decimal_value(row.get("policy_annual_premium"), "1")
        deductible = decimal_value(row.get("policy_deductable"))
        user, policy, vehicle = self.import_related(
            source="insurance", source_id=policy_number, policy_number=policy_number,
            incident_date=incident_date, state=state, premium=premium, deductible=deductible,
            make=make, model=model, year=row.get("auto_year"), age=age, raw_data=row,
        )

        incident_map = {"Vehicle Theft": IncidentType.THEFT, "Parked Car": IncidentType.OTHER,
                        "Single Vehicle Collision": IncidentType.COLLISION,
                        "Multi-vehicle Collision": IncidentType.COLLISION}
        severity_map = {"Trivial Damage": IncidentSeverity.MINOR, "Minor Damage": IncidentSeverity.MINOR,
                        "Major Damage": IncidentSeverity.MAJOR, "Total Loss": IncidentSeverity.TOTAL_LOSS}
        fraud = truthy(row.get("fraud_reported"))
        amount = decimal_value(row.get("total_claim_amount"))
        features = {"source_dataset": "insurance_claims", "fraud_reported": row.get("fraud_reported"),
                    "source_data": row}
        Claim.objects.update_or_create(
            claim_number=claim_key,
            defaults={"customer": user, "policy": policy, "vehicle": vehicle,
                      "incident_date": incident_date,
                      "incident_type": incident_map.get(row.get("incident_type"), IncidentType.OTHER),
                      "incident_severity": severity_map.get(row.get("incident_severity"), IncidentSeverity.MODERATE),
                      "location": ", ".join(filter(None, [row.get("incident_location"), row.get("incident_city"), state])),
                      "number_of_vehicles": max(1, int(float(row.get("number_of_vehicles_involved") or 1))),
                      "injuries": int(float(row.get("bodily_injuries") or 0)) > 0,
                      "injury_details": f"{row.get('bodily_injuries', '0')} bodily injuries reported",
                      "property_damage": truthy(row.get("property_damage")),
                      "witnesses": int(float(row.get("witnesses") or 0)) > 0,
                      "police_report": truthy(row.get("police_report_available")), "claim_amount": amount,
                      "description": "Imported insurance claims sample. See AI assessment source data for original fields.",
                      "status": ClaimStatus.INVESTIGATION if fraud else ClaimStatus.CLOSED,
                      "priority": ClaimPriority.HIGH if fraud else ClaimPriority.MEDIUM,
                      "fraud_risk_score": Decimal("85.00") if fraud else Decimal("10.00"),
                      "total_loss_probability": Decimal("95.00") if row.get("incident_severity") == "Total Loss" else Decimal("5.00"),
                      "ai_assessment": features},
        )

    def import_fraud_row(self, row):
        source_id = str(row["PolicyNumber"]).strip()
        claim_key = f"FO-{source_id}"[:20]
        incident_date = month_date(row.get("Month"), row.get("Year"), row.get("WeekOfMonth", 3))
        age = int(float(row.get("Age") or 35))
        state = "NA"
        policy_number = source_id
        premium = Decimal("1200.00")
        deductible = decimal_value(row.get("Deductible"), "400")
        user, policy, vehicle = self.import_related(
            source="fraudoracle", source_id=source_id, policy_number=policy_number,
            incident_date=incident_date, state=state, premium=premium, deductible=deductible,
            make=row.get("Make", "Unknown"), model=row.get("VehicleCategory", "Unknown"),
            year=row.get("Year"), age=age, raw_data=row,
        )

        fraud = str(row.get("FraudFound_P", "0")).strip() == "1"
        price = row.get("VehiclePrice", "")
        amount = Decimal("70000") if "69000" in price else Decimal("24000")
        incident_type = IncidentType.THEFT if "Theft" in str(row.get("PolicyType", "")) else IncidentType.COLLISION
        features = {"source_dataset": "fraud_oracle", "fraud_reported": int(fraud), "source_data": row}
        Claim.objects.update_or_create(
            claim_number=claim_key,
            defaults={"customer": user, "policy": policy, "vehicle": vehicle,
                      "incident_date": incident_date, "incident_type": incident_type,
                      "incident_severity": IncidentSeverity.MODERATE,
                      "location": f"{row.get('AccidentArea', 'Unknown')} area",
                      "number_of_vehicles": 1, "injuries": False,
                      "property_damage": False, "witnesses": truthy(row.get("WitnessPresent")),
                      "police_report": truthy(row.get("PoliceReportFiled")), "claim_amount": amount,
                      "description": "Imported Fraud Oracle sample. See AI assessment source data for original fields.",
                      "status": ClaimStatus.INVESTIGATION if fraud else ClaimStatus.CLOSED,
                      "priority": ClaimPriority.HIGH if fraud else ClaimPriority.MEDIUM,
                      "fraud_risk_score": Decimal("85.00") if fraud else Decimal("10.00"),
                      "total_loss_probability": Decimal("5.00"), "ai_assessment": features},
        )
