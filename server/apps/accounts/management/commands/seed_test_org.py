"""
Management command — implementation not published in this demo.
Live product: https://developeros.pro
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import Organization, UserProfile

class Command(BaseCommand):
        help = "Seed a deterministic test org + admin user and mint a JWT pair for UAT."
        def add_arguments(self, parser):
        pass  # implementation not published

        def handle(self, *args, **opts):
        pass  # implementation not published

