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
        parser.add_argument(
            "--org",
            type=int,
            help="Seed records for a specific organization ID only.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove obsolete seeded rows for the same seeded keys/codes.",
        )

    def handle(self, *args, **options):
        org_id = options.get("org")
        reset = options.get("reset", False)

        payloads = self._load_payloads()

        if org_id:
            try:
                orgs = [Organization.objects.get(pk=org_id)]
            except Organization.DoesNotExist as exc:
                raise CommandError(f"Organization {org_id} not found.") from exc
        else:
            orgs = list(Organization.objects.all())

        if not orgs:
            self.stdout.write(self.style.WARNING("No organizations found."))
            return

        totals = {
            "notification_templates_created": 0,
            "notification_templates_updated": 0,
            "workflow_templates_created": 0,
            "workflow_templates_updated": 0,
            "workflow_steps_created": 0,
            "workflow_steps_updated": 0,
            "approval_policies_created": 0,
            "approval_policies_updated": 0,
            "access_policies_created": 0,
            "access_policies_updated": 0,
            "policy_conditions_created": 0,
            "policy_conditions_updated": 0,
            "policy_actions_created": 0,
            "policy_actions_updated": 0,
            "reset_deleted": 0,
            "missing_content_types": 0,
            "event_key_warnings": 0,
            "email_template_warnings": 0,
        }

        for org in orgs:
            result = self._seed_org(
                org=org,
                reset=reset,
                event_keys=payloads["event_keys"],
                email_templates=payloads["email_templates"],
                notification_templates=payloads["notification_templates"],
                workflow_payload=payloads["workflows"],
                access_policy_payload=payloads["access_policies"],
            )
            for key, value in result.items():
                totals[key] += value

            self.stdout.write(

                    f"  {org.name}: "
                    f"notification_templates +{result['notification_templates_created']}/~{result['notification_templates_updated']}, "
                    f"workflow_templates +{result['workflow_templates_created']}/~{result['workflow_templates_updated']}, "
                    f"workflow_steps +{result['workflow_steps_created']}/~{result['workflow_steps_updated']}, "
                    f"approval_policies +{result['approval_policies_created']}/~{result['approval_policies_updated']}, "
                    f"access_policies +{result['access_policies_created']}/~{result['access_policies_updated']}, "
                    f"policy_conditions +{result['policy_conditions_created']}/~{result['policy_conditions_updated']}, "
                    f"policy_actions +{result['policy_actions_created']}/~{result['policy_actions_updated']}"
                    + (
                        f", reset-deleted {result['reset_deleted']}"
                        if reset
                        else ""
                    )

            )

        summary = (
            f"Done across {len(orgs)} org(s). "
            f"notification_templates +{totals['notification_templates_created']}/~{totals['notification_templates_updated']}, "
            f"workflow_templates +{totals['workflow_templates_created']}/~{totals['workflow_templates_updated']}, "
            f"workflow_steps +{totals['workflow_steps_created']}/~{totals['workflow_steps_updated']}, "
            f"approval_policies +{totals['approval_policies_created']}/~{totals['approval_policies_updated']}, "
            f"access_policies +{totals['access_policies_created']}/~{totals['access_policies_updated']}, "
            f"policy_conditions +{totals['policy_conditions_created']}/~{totals['policy_conditions_updated']}, "
            f"policy_actions +{totals['policy_actions_created']}/~{totals['policy_actions_updated']}"
            + (f", reset-deleted {totals['reset_deleted']}" if reset else "")
        )
        self.stdout.write(self.style.SUCCESS(summary))

        if totals["missing_content_types"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {totals['missing_content_types']} items due to missing content types."
                )
            )
        if totals["event_key_warnings"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {totals['event_key_warnings']} notification templates with unknown event_key."
                )
            )
        if totals["email_template_warnings"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {totals['email_template_warnings']} email templates with unknown email_html_key."
                )
            )

    def _load_payloads(self) -> dict[str, Any]:
        base_dir = (
            Path(__file__).resolve().parents[2]
            / "seed_data"
            / "platform_governance"
        )
        if not base_dir.exists():
            raise CommandError(f"Seed data path not found: {base_dir}")

        event_keys = self._load_json(base_dir / "event_keys.json")
        email_templates_list = self._load_json(base_dir / "email_html_templates.json")
        notification_templates = self._load_json(
            base_dir / "notification_templates.json"
        )
        workflows = self._load_json(base_dir / "workflows.json")
        access_policies = self._load_json(base_dir / "access_policies.json")

        email_templates = {}
        for item in email_templates_list:
            key = (item or {}).get("key")
            html = (item or {}).get("html", "")
            if key:
                email_templates[str(key)] = str(html)

        return {
            "event_keys": event_keys,
            "email_templates": email_templates,
            "notification_templates": notification_templates,
            "workflows": workflows,
            "access_policies": access_policies,
        }

    def _load_json(self, path: Path) -> Any:
        if not path.exists():
            raise CommandError(f"Seed file not found: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {path}: {exc}") from exc

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
        counts = {
            "notification_templates_created": 0,
            "notification_templates_updated": 0,
            "workflow_templates_created": 0,
            "workflow_templates_updated": 0,
            "workflow_steps_created": 0,
            "workflow_steps_updated": 0,
            "approval_policies_created": 0,
            "approval_policies_updated": 0,
            "access_policies_created": 0,
            "access_policies_updated": 0,
            "policy_conditions_created": 0,
            "policy_conditions_updated": 0,
            "policy_actions_created": 0,
            "policy_actions_updated": 0,
            "reset_deleted": 0,
            "missing_content_types": 0,
            "event_key_warnings": 0,
            "email_template_warnings": 0,
        }

        event_key_catalog = {
            str((item or {}).get("key", "")).strip()
            for item in event_keys
            if (item or {}).get("key")
        }

        notification_codes = self._seed_notification_templates(
            org=org,
            counts=counts,
            event_key_catalog=event_key_catalog,
            email_templates=email_templates,
            templates=notification_templates,
        )
        if reset and notification_codes:
            deleted, _ = (
                NotificationTemplate.objects.filter(
                    organization=org,
                    code__startswith="seed_",
                )
                .exclude(code__in=notification_codes)
                .delete()
            )
            counts["reset_deleted"] += deleted

        self._seed_workflow_templates(
            org=org,
            reset=reset,
            counts=counts,
            workflow_payload=workflow_payload,
        )

        self._seed_access_policies(
            org=org,
            reset=reset,
            counts=counts,
            access_policy_payload=access_policy_payload,
        )

        return counts

    def _seed_notification_templates(
        self,
        *,
        org,
        counts: dict[str, int],
        event_key_catalog: set[str],
        email_templates: dict[str, str],
        templates: list[dict[str, Any]],
    ) -> set[str]:
        seen_codes: set[str] = set()

        for row in templates:
            code = str((row or {}).get("code", "")).strip()
            if not code:
                continue
            seen_codes.add(code)

            event_key = str((row or {}).get("event_key", "")).strip()
            if event_key and event_key_catalog and event_key not in event_key_catalog:
                counts["event_key_warnings"] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  {org.name}: unknown event key '{event_key}' for template '{code}'."
                    )
                )

            email_html_key = str((row or {}).get("email_html_key", "")).strip()
            body_html = ""
            if email_html_key:
                body_html = email_templates.get(email_html_key, "")
                if not body_html:
                    counts["email_template_warnings"] += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {org.name}: unknown email_html_key '{email_html_key}' for template '{code}'."
                        )
                    )

            defaults = {
                "name": str((row or {}).get("name", code)),
                "description": str((row or {}).get("description", "")),
                "channel": str((row or {}).get("channel", "in_app")),
                "event_key": event_key,
                "severity_tier": str((row or {}).get("severity_tier", "review")),
                "subject": str((row or {}).get("subject", "")),
                "body_text": str((row or {}).get("body_text", "")),
                "body_html": body_html,
                "variables": list((row or {}).get("variables") or []),
                "is_active": bool((row or {}).get("is_active", True)),
                "is_system": bool((row or {}).get("is_system", True)),
            }

            _, created = NotificationTemplate.objects.update_or_create(
                organization=org,
                code=code,
                defaults=defaults,
            )
            if created:
                counts["notification_templates_created"] += 1
            else:
                counts["notification_templates_updated"] += 1

        return seen_codes

    def _seed_workflow_templates(
        self,
        *,
        org,
        reset: bool,
        counts: dict[str, int],
        workflow_payload: dict[str, Any],
    ) -> set[str]:
        seen_codes: set[str] = set()
        templates = list((workflow_payload or {}).get("templates") or [])

        for row in templates:
            code = str((row or {}).get("code", "")).strip()
            if not code:
                continue
            seen_codes.add(code)

            template_defaults = {
                "name": str((row or {}).get("name", code)),
                "description": str((row or {}).get("description", "")),
                "default_step_mode": str(
                    (row or {}).get("default_step_mode", "sequential")
                ),
                "is_default": bool((row or {}).get("is_default", False)),
                "is_active": bool((row or {}).get("is_active", True)),
            }
            template, created = WorkflowTemplate.objects.update_or_create(
                organization=org,
                code=code,
                defaults=template_defaults,
            )
            if created:
                counts["workflow_templates_created"] += 1
            else:
                counts["workflow_templates_updated"] += 1

            content_types = self._resolve_content_types(
                rows=(row or {}).get("applicable_content_types") or [],
                counts=counts,
                org_name=org.name,
                context=f"workflow template '{code}'",
            )
            template.applicable_content_types.set(content_types)

            seen_step_sequences: set[int] = set()
            for step_row in (row or {}).get("steps") or []:
                sequence = int((step_row or {}).get("sequence") or 0)
                if sequence <= 0:
                    continue
                seen_step_sequences.add(sequence)

                step_defaults = {
                    "name": str((step_row or {}).get("name", f"Step {sequence}")),
                    "step_type": str((step_row or {}).get("step_type", "approval")),
                    "execution_mode": str(
                        (step_row or {}).get("execution_mode", "sequential")
                    ),
                    "approver_role_slug": str(
                        (step_row or {}).get("approver_role_slug", "")
                    ),
                    "sla_hours": (step_row or {}).get("sla_hours"),
                    "escalation_role_slug": str(
                        (step_row or {}).get("escalation_role_slug", "")
                    ),
                    "condition_field": str(
                        (step_row or {}).get("condition_field", "")
                    ),
                    "condition_operator": str(
                        (step_row or {}).get("condition_operator", "")
                    ),
                    "condition_value": str(
                        (step_row or {}).get("condition_value", "")
                    ),
                    "condition_true_step": (step_row or {}).get("condition_true_step"),
                    "condition_false_step": (step_row or {}).get("condition_false_step"),
                    "is_active": bool((step_row or {}).get("is_active", True)),
                }
                _, step_created = WorkflowTemplateStep.objects.update_or_create(
                    template=template,
                    sequence=sequence,
                    defaults=step_defaults,
                )
                if step_created:
                    counts["workflow_steps_created"] += 1
                else:
                    counts["workflow_steps_updated"] += 1

            if reset:
                step_qs = template.steps.all()
                if seen_step_sequences:
                    deleted, _ = step_qs.exclude(
                        sequence__in=seen_step_sequences
                    ).delete()
                else:
                    deleted, _ = step_qs.delete()
                counts["reset_deleted"] += deleted

            seen_policy_names: set[str] = set()
            for policy_row in (row or {}).get("approval_policies") or []:
                policy_name = str((policy_row or {}).get("name", "")).strip()
                if not policy_name:
                    continue
                seen_policy_names.add(policy_name)

                content_type_ref = (policy_row or {}).get("content_type") or {}
                app_label = str(content_type_ref.get("app_label", "")).strip()
                model = str(content_type_ref.get("model", "")).strip()
                content_type = ContentType.objects.filter(
                    app_label=app_label,
                    model=model,
                ).first()
                if not content_type:
                    counts["missing_content_types"] += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {org.name}: missing content type '{app_label}.{model}' for approval policy '{policy_name}'."
                        )
                    )
                    continue

                defaults = {
                    "policy_type": str(
                        (policy_row or {}).get("policy_type", "financial_threshold")
                    ),
                    "content_type": content_type,
                    "amount_field": str(
                        (policy_row or {}).get("amount_field", "total_amount")
                    ),
                    "min_amount": _decimal_or_none((policy_row or {}).get("min_amount")),
                    "max_amount": _decimal_or_none((policy_row or {}).get("max_amount")),
                    "priority": int((policy_row or {}).get("priority") or 100),
                    "is_active": bool((policy_row or {}).get("is_active", True)),
                }
                _, policy_created = ApprovalPolicy.objects.update_or_create(
                    organization=org,
                    template=template,
                    name=policy_name,
                    defaults=defaults,
                )
                if policy_created:
                    counts["approval_policies_created"] += 1
                else:
                    counts["approval_policies_updated"] += 1

            if reset:
                policy_qs = template.policies.all()
                if seen_policy_names:
                    deleted, _ = policy_qs.exclude(name__in=seen_policy_names).delete()
                else:
                    deleted, _ = policy_qs.delete()
                counts["reset_deleted"] += deleted

        return seen_codes

    def _seed_access_policies(
        self,
        *,
        org,
        reset: bool,
        counts: dict[str, int],
        access_policy_payload: dict[str, Any],
    ) -> set[str]:
        seen_keys: set[str] = set()
        policies = list((access_policy_payload or {}).get("policies") or [])

        for row in policies:
            key = str((row or {}).get("key", "")).strip()
            if not key:
                continue
            seen_keys.add(key)

            defaults = {
                "name": str((row or {}).get("name", key)),
                "description": str((row or {}).get("description", "")),
                "module": str((row or {}).get("module", "")),
                "sub_module": str((row or {}).get("sub_module", "")),
                "action": str((row or {}).get("action", "")),
                "priority": int((row or {}).get("priority") or 100),
                "is_active": bool((row or {}).get("is_active", True)),
            }
            policy, created = AccessPolicy.objects.update_or_create(
                organization=org,
                key=key,
                defaults=defaults,
            )
            if created:
                counts["access_policies_created"] += 1
            else:
                counts["access_policies_updated"] += 1

            seen_condition_keys: set[tuple[str, str, int]] = set()
            for idx, condition_row in enumerate((row or {}).get("conditions") or []):
                condition_type = str(
                    (condition_row or {}).get("condition_type", "")
                ).strip()
                operator = str((condition_row or {}).get("operator", "eq")).strip()
                sort_order = int((condition_row or {}).get("sort_order") or (idx + 1) * 10)
                if not condition_type:
                    continue

                condition_key = (condition_type, operator, sort_order)
                seen_condition_keys.add(condition_key)
                condition_defaults = {
                    "value": (condition_row or {}).get("value"),
                    "is_active": bool((condition_row or {}).get("is_active", True)),
                }
                _, condition_created = PolicyCondition.objects.update_or_create(
                    access_policy=policy,
                    condition_type=condition_type,
                    operator=operator,
                    sort_order=sort_order,
                    defaults=condition_defaults,
                )
                if condition_created:
                    counts["policy_conditions_created"] += 1
                else:
                    counts["policy_conditions_updated"] += 1

            if reset:
                condition_qs = policy.conditions.all()
                if seen_condition_keys:
                    for condition in condition_qs:
                        condition_key = (
                            condition.condition_type,
                            condition.operator,
                            condition.sort_order,
                        )
                        if condition_key in seen_condition_keys:
                            continue
                        condition.delete()
                        counts["reset_deleted"] += 1
                else:
                    deleted, _ = condition_qs.delete()
                    counts["reset_deleted"] += deleted

            seen_action_keys: set[tuple[str, int]] = set()
            for idx, action_row in enumerate((row or {}).get("actions") or []):
                action_type = str((action_row or {}).get("action_type", "")).strip()
                sort_order = int((action_row or {}).get("sort_order") or (idx + 1) * 10)
                if not action_type:
                    continue

                action_key = (action_type, sort_order)
                seen_action_keys.add(action_key)
                action_defaults = {
                    "parameters": (action_row or {}).get("parameters") or {},
                    "message": str((action_row or {}).get("message", "")),
                    "is_active": bool((action_row or {}).get("is_active", True)),
                }
                _, action_created = PolicyAction.objects.update_or_create(
                    access_policy=policy,
                    action_type=action_type,
                    sort_order=sort_order,
                    defaults=action_defaults,
                )
                if action_created:
                    counts["policy_actions_created"] += 1
                else:
                    counts["policy_actions_updated"] += 1

            if reset:
                action_qs = policy.policy_actions.all()
                if seen_action_keys:
                    for policy_action in action_qs:
                        action_key = (
                            policy_action.action_type,
                            policy_action.sort_order,
                        )
                        if action_key in seen_action_keys:
                            continue
                        policy_action.delete()
                        counts["reset_deleted"] += 1
                else:
                    deleted, _ = action_qs.delete()
                    counts["reset_deleted"] += deleted

        return seen_keys

    def _resolve_content_types(
        self,
        *,
        rows: list[dict[str, Any]],
        counts: dict[str, int],
        org_name: str,
        context: str,
    ) -> list[ContentType]:
        resolved: list[ContentType] = []
        seen_keys: set[tuple[str, str]] = set()

        for row in rows:
            app_label = str((row or {}).get("app_label", "")).strip()
            model = str((row or {}).get("model", "")).strip()
            if not app_label or not model:
                continue
            key = (app_label, model)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            content_type = ContentType.objects.filter(
                app_label=app_label,
                model=model,
            ).first()
            if not content_type:
                counts["missing_content_types"] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  {org_name}: missing content type '{app_label}.{model}' for {context}."
                    )
                )
                continue
            resolved.append(content_type)

        return resolved


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
