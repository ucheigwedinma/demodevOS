"""
Management command — implementation not published in this demo.
Live product: https://developeros.pro
"""

from django.core.management.base import BaseCommand
from apps.settings.models import ADDON_ONLY_MODULES, Module, PlatformEdition

class Command(BaseCommand):
        help = "Seed platform edition definitions. Idempotent."
        def handle(self, *args, **options):
        pass  # implementation not published

