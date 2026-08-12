import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


TRUE_VALUES = {"1", "true", "yes", "on"}


class Command(BaseCommand):
    help = "Create the default superuser once when it does not already exist."

    def handle(self, *args, **options):
        enabled = os.environ.get("DEFAULT_ADMIN_ENABLED", "true").strip().lower() in TRUE_VALUES
        if not enabled:
            self.stdout.write("Default admin bootstrap disabled.")
            return

        username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin").strip() or "admin"
        password = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin")
        email = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@localhost").strip()

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Default admin '{username}' already exists; leaving credentials unchanged.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Default admin '{username}' created."))
