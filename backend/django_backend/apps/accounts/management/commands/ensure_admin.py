"""Create the first administrator from environment variables, once.

Free hosting tiers such as Render's have no shell for ``createsuperuser``, so the
build runs this command. It does nothing when the variables are unset or the
account already exists, so it is safe to run on every deploy.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create an admin from DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD if it does not exist."

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip().lower()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not email or not password:
            self.stdout.write("DJANGO_SUPERUSER_EMAIL/PASSWORD not set; skipping admin creation.")
            return
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            self.stdout.write(f"Admin {email} already exists; leaving it unchanged.")
            return
        User.objects.create_superuser(
            username=os.environ.get("DJANGO_SUPERUSER_USERNAME", "") or email.split("@")[0],
            email=email,
            password=password,
            first_name="Admin",
        )
        self.stdout.write(self.style.SUCCESS(f"Created admin {email}."))
