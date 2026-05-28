"""
Management command — implementation not published in this demo.
Live product: https://developeros.pro
"""

from django.core.management.base import BaseCommand
from apps.settings.seed_templates import seed_global_project_templates

class Command(BaseCommand):
        help = "Seed global system project templates (organisation=NULL). Idempotent."
        def handle(self, *args, **options):
        pass  # implementation not published

