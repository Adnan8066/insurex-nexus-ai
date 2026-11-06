"""Export closed claims with a recorded fraud outcome to CSV, for model training.

Only claims with outcome fraud, genuine or unclear are exported. Personal details
(names, phone numbers, addresses) are not included. Claims marked unclear are
written out too, so they can be filtered out before training.
"""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.claims.models import Claim

COLUMNS = [
    'claim_id', 'claim_date', 'reported_date', 'policy_start_date', 'district',
    'vehicle_make', 'vehicle_model', 'vehicle_year', 'claimed_amount_inr',
    'estimated_repair_inr', 'police_report', 'witnesses', 'past_claims_count',
    'outcome', 'outcome_date',
]


def _yes_no(value):
    return 'Y' if value else 'N'


class Command(BaseCommand):
    help = 'Export claims that have a recorded fraud outcome to a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('output', help='Path of the CSV file to write, e.g. kerala_claims.csv')

    def handle(self, *args, **options):
        output = Path(options['output'])
        claims = (
            Claim.objects.exclude(fraud_outcome='')
            .select_related('vehicle', 'policy')
            .order_by('incident_date', 'pk')
        )
        count = 0
        with output.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            for claim in claims:
                earlier = Claim.objects.filter(
                    customer_id=claim.customer_id, incident_date__lt=claim.incident_date,
                ).count()
                vehicle = claim.vehicle
                writer.writerow({
                    'claim_id': claim.claim_number,
                    'claim_date': claim.incident_date.isoformat() if claim.incident_date else '',
                    'reported_date': claim.submitted_at.date().isoformat() if claim.submitted_at else '',
                    'policy_start_date': claim.policy.start_date.isoformat() if claim.policy and claim.policy.start_date else '',
                    'district': claim.location or '',
                    'vehicle_make': vehicle.make if vehicle else '',
                    'vehicle_model': vehicle.model if vehicle else '',
                    'vehicle_year': vehicle.year if vehicle else '',
                    'claimed_amount_inr': claim.claim_amount,
                    'estimated_repair_inr': claim.estimated_repair_cost,
                    'police_report': _yes_no(claim.police_report),
                    'witnesses': _yes_no(claim.witnesses),
                    'past_claims_count': earlier,
                    'outcome': claim.fraud_outcome,
                    'outcome_date': claim.fraud_outcome_date.isoformat() if claim.fraud_outcome_date else '',
                })
                count += 1
        if count == 0:
            raise CommandError('No claims have a recorded fraud outcome yet.')
        self.stdout.write(self.style.SUCCESS(f'Exported {count} claims to {output}'))
