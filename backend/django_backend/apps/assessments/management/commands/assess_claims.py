"""Score existing claims with the trained models and refresh their fraud alerts."""

from django.core.management.base import BaseCommand

from apps.assessments.ai_views import run_claim_assessment
from apps.claims.models import Claim
from ml_service import MLModelUnavailable


class Command(BaseCommand):
    help = (
        "Run the AI assessment on claims filed through the app so their fraud and "
        "total-loss scores reach dashboards and the fraud alert queue."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-imported",
            action="store_true",
            help="Also re-score claims loaded by import_project_datasets (slow for the full datasets).",
        )

    def handle(self, *args, **options):
        claims = Claim.objects.select_related("customer", "policy", "vehicle").order_by("id")
        scored = skipped = 0
        for claim in claims.iterator():
            imported = isinstance(claim.ai_assessment, dict) and claim.ai_assessment.get("source_dataset")
            if imported and not options["include_imported"]:
                continue
            try:
                assessment = run_claim_assessment(claim)
            except MLModelUnavailable as exc:
                skipped += 1
                self.stderr.write(f"{claim.claim_number}: skipped ({exc})")
                continue
            scored += 1
            self.stdout.write(
                f"{claim.claim_number}: fraud {assessment.fraud_risk_score:.1f} ({assessment.risk_level}), "
                f"total loss {assessment.total_loss_probability:.1f}%"
            )
        self.stdout.write(self.style.SUCCESS(f"Scored {scored} claim(s); skipped {skipped}."))
