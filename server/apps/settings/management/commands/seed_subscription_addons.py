"""
Management command — implementation not published in this demo.
Live product: https://developeros.pro
"""

from django.core.management.base import BaseCommand
from apps.settings.models import SubscriptionAddOn

class Command(BaseCommand):
        help = "Seed subscription add-on products (module and storage add-ons)"
        def handle(self, *args, **options):
        pass  # implementation not published

