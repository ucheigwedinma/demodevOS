"""
Management command — implementation not published in this demo.
Live product: https://developeros.pro
"""

from django.core.management.base import BaseCommand
from apps.accounts.models import Organization
from apps.settings.scope_defaults import seed_role_scopes_for_org, seed_user_scope_assignments_for_org

class Command(BaseCommand):
        help = "Seed layered access data scopes (role scopes + user scope assignments)."
        def add_arguments(self, parser):
        pass  # implementation not published

        def handle(self, *args, **options):
        pass  # implementation not published

