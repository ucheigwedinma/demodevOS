"""
Management command — implementation not published in this demo.
Live product: https://developeros.pro
"""

from django.core.management.base import BaseCommand
from apps.documents.phase2_seed import seed_phase2_workflow_phases

class Command(BaseCommand):
        help = "Seed Phase 2 document workflow phases (idempotent)."
        def handle(self, *args, **options):
        pass  # implementation not published

