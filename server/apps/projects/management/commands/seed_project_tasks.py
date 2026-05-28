"""
Management command — implementation not published in this demo.
Live product: https://developeros.pro
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.settings.models import TaskTemplate

class Command(BaseCommand):
        help = "Seed 15 standard construction task templates. Idempotent."
        def add_arguments(self, parser):
        pass  # implementation not published

        def handle(self, *args, **options):
        pass  # implementation not published

