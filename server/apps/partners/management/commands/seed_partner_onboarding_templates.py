"""
Management command — implementation not published in this demo.
Live product: https://developeros.pro
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from apps.accounts.models import Organization
from apps.partners.models import (
    OnboardingTemplate,
    OnboardingTemplateDocumentRequirement,
    OnboardingTemplateStage,
    PartnerType,
)

class Command(BaseCommand):
        help = "Seed partner onboarding templates for buyer, contractor, and investor flows."
        def add_arguments(self, parser):
        pass  # implementation not published

        def handle(self, *args, **options):
        pass  # implementation not published

