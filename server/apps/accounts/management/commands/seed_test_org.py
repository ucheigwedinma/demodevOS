"""
Idempotent seed for end-to-end / UAT tests.

Creates (or reuses) a deterministic Organization + admin User, then mints a
JWT pair via SimpleJWT and writes a credentials file consumed by Playwright's
global setup.

Refuses to run unless DEBUG is True OR DEVOS_ALLOW_TEST_SEED=1 is set, so the
command cannot accidentally create a backdoor user in production.

Usage:
    python manage.py seed_test_org \\
        --output e2e/.auth/credentials.json
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

User = get_user_model()


TEST_ORG_NAME = "Playwright Test Org"
TEST_USERNAME = "playwright-admin"
TEST_EMAIL = "playwright-admin@uat.local"
TEST_PASSWORD = "Playwright!UAT!2026"


class Command(BaseCommand):
    help = "Seed a deterministic test org + admin user and mint a JWT pair for UAT."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="e2e/.auth/credentials.json",
            help="Path (relative to BASE_DIR/..) where credentials JSON is written.",
        )

    def handle(self, *args, **opts):
        if not settings.DEBUG and os.environ.get("DEVOS_ALLOW_TEST_SEED") != "1":
            raise CommandError(
                "Refusing to run seed_test_org outside DEBUG. "
                "Set DEVOS_ALLOW_TEST_SEED=1 to override (do NOT do this in production)."
            )

        with transaction.atomic():
            org, org_created = Organization.objects.get_or_create(
                name=TEST_ORG_NAME,
                defaults={
                    "legal_name": TEST_ORG_NAME,
                    "industry": "Real Estate",
                    "country": "Pakistan",
                },
            )

            user, user_created = User.objects.get_or_create(
                username=TEST_USERNAME,
                defaults={
                    "email": TEST_EMAIL,
                    "first_name": "Playwright",
                    "last_name": "Admin",
                    "is_active": True,
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            user.set_password(TEST_PASSWORD)
            user.save()

            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={"organization": org, "role": "admin"},
            )
            if profile.organization_id != org.id or profile.role != "admin":
                profile.organization = org
                profile.role = "admin"
                profile.save()

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_str = str(refresh)

        payload = {
            "access_token": access,
            "refresh_token": refresh_str,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
            "organization": {
                "id": org.id,
                "name": org.name,
            },
            "password": TEST_PASSWORD,
        }

        out_path = Path(opts["output"]).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2))
        try:
            os.chmod(out_path, 0o600)
        except OSError:
            pass

        verbs = []
        verbs.append(f"org {'created' if org_created else 'reused'}")
        verbs.append(f"user {'created' if user_created else 'reused'}")
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_test_org: {', '.join(verbs)}. Credentials at {out_path}"
            )
        )
