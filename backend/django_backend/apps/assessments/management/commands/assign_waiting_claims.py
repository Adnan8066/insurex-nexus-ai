"""Retry automatic hand-off of waiting claims and policy requests."""

from django.core.management.base import BaseCommand

from apps.assessments.assignment import assign_waiting_work


class Command(BaseCommand):
    help = "Route unassigned open claims through the RL model (e.g. after deploying a qualified model)."

    def handle(self, *args, **options):
        requests_assigned, claims_assigned = assign_waiting_work()
        self.stdout.write(self.style.SUCCESS(
            f"Assigned {claims_assigned} waiting claim(s) and {requests_assigned} policy request(s)."
        ))
