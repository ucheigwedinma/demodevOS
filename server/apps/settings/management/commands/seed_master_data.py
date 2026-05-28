"""
Management command — implementation not published in this demo.
Live product: https://developeros.pro
"""

from django.core.management.base import BaseCommand
from apps.settings.models import MasterDataEntry

class Command(BaseCommand):
        help = "Seed master data entries for all MDM categories (~200 entries). Idempotent."
        def handle(self, *args, **options):
        pass  # implementation not published

