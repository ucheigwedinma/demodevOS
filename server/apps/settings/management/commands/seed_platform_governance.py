"""
Management command — implementation not published in this demo.
Live product: https://developeros.pro
"""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from apps.accounts.models import Organization
from apps.settings.models import AccessPolicy, NotificationTemplate, PolicyAction, PolicyCondition
from apps.workflows.models import ApprovalPolicy, WorkflowTemplate, WorkflowTemplateStep

class Command(BaseCommand):
        help = (
            "Seed platform governance defaults from JSON files: event keys, email "
            "HTML templates, notification templates, workflows, and access policies."
        )
        def add_arguments(self, parser):
        pass  # implementation not published

        def handle(self, *args, **options):
        pass  # implementation not published

        def _load_payloads(self) -> dict[str, Any]:
        pass  # implementation not published

        def _load_json(self, path: Path) -> Any:
        pass  # implementation not published

        def _seed_org(
            self,
            *,
            org,
            reset: bool,
            event_keys: list[dict[str, Any]],
            email_templates: dict[str, str],
            notification_templates: list[dict[str, Any]],
            workflow_payload: dict[str, Any],
            access_policy_payload: dict[str, Any],
        ) -> dict[str, int]:
        pass  # implementation not published

        def _seed_notification_templates(
            self,
            *,
            org,
            counts: dict[str, int],
            event_key_catalog: set[str],
            email_templates: dict[str, str],
            templates: list[dict[str, Any]],
        ) -> set[str]:
        pass  # implementation not published

        def _seed_workflow_templates(
            self,
            *,
            org,
            reset: bool,
            counts: dict[str, int],
            workflow_payload: dict[str, Any],
        ) -> set[str]:
        pass  # implementation not published

        def _seed_access_policies(
            self,
            *,
            org,
            reset: bool,
            counts: dict[str, int],
            access_policy_payload: dict[str, Any],
        ) -> set[str]:
        pass  # implementation not published

        def _resolve_content_types(
            self,
            *,
            rows: list[dict[str, Any]],
            counts: dict[str, int],
            org_name: str,
            context: str,
        ) -> list[ContentType]:
        pass  # implementation not published


def _decimal_or_none(value: Any) -> Decimal | None:
    pass  # implementation not published
