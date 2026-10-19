"""Create local-only, non-login demo candidates for routing advice."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.assessments.models import RoutingAgentProfile


DEMO_AGENTS = (
    {"username": "demo-routing-aarav-sharma", "first_name": "Aarav", "last_name": "Sharma", "role": "employee", "skill_tier": 4},
    {"username": "demo-routing-priya-nair", "first_name": "Priya", "last_name": "Nair", "role": "investigator", "skill_tier": 5},
    {"username": "demo-routing-rohan-patel", "first_name": "Rohan", "last_name": "Patel", "role": "employee", "skill_tier": 3},
)


class Command(BaseCommand):
    help = "Seed three local demo routing candidates (do not run in production)."

    def handle(self, *args, **options):
        User = get_user_model()
        for data in DEMO_AGENTS:
            email = f"{data['username']}@example.invalid"
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": email,
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "role": data["role"],
                    "is_active": True,
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            if not created and (not user.email.endswith("@example.invalid") or user.is_staff or user.is_superuser):
                raise CommandError(f"Refusing to modify non-demo account {user.username!r}.")
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            profile, profile_created = RoutingAgentProfile.objects.get_or_create(
                user=user,
                defaults={"skill_tier": data["skill_tier"], "is_available": True, "is_demo": True},
            )
            if not profile.is_demo:
                raise CommandError(f"Refusing to mark existing real profile for {user.username!r} as demo.")
            state = "created" if created and profile_created else "already present"
            self.stdout.write(f"{state}: {user.get_full_name()} (tier {profile.skill_tier})")
