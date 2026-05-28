from django.core.management.base import BaseCommand

from apps.settings.seed_templates import seed_global_project_templates


class Command(BaseCommand):
    help = "Seed global system project templates (organisation=NULL). Idempotent."

    def handle(self, *args, **options):
        count = seed_global_project_templates()
        self.stdout.write(
            self.style.SUCCESS(f"Done. {count} global template(s) created.")
        )
