import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import Organization
from apps.settings.models import KpiDefinition, Role

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Seed canonical KPI metrics contracts (KPI, dimensions, grain, owner, "
        "freshness SLA) for organizations."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=int,
            help="Seed records for a specific organization ID only.",
        )

    def handle(self, *args, **options):
        payload = self._load_payload()

        org_id = options.get("org")
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
            "created": 0,
            "updated": 0,
            "role_warnings": 0,
            "role_fallbacks": 0,
            "user_warnings": 0,
        }

        for org in orgs:
            result = self._seed_org(org, payload)
            for key in totals:
                totals[key] += result.get(key, 0)

            self.stdout.write(

                    f"  {org.name}: kpis +{result['created']}/~{result['updated']}"
                    f", missing-role {result['role_warnings']}"
                    f", fallback-role {result['role_fallbacks']}"
                    f", missing-user {result['user_warnings']}"

            )

        self.stdout.write(
            self.style.SUCCESS(

                    f"Done across {len(orgs)} org(s). "
                    f"kpis +{totals['created']}/~{totals['updated']}, "
                    f"missing-role {totals['role_warnings']}, "
                    f"fallback-role {totals['role_fallbacks']}, "
                    f"missing-user {totals['user_warnings']}"

            )
        )

    def _load_payload(self) -> list[dict[str, Any]]:
        payload_path = (
            Path(__file__).resolve().parents[2]
            / "seed_data"
            / "metrics_contract"
            / "canonical_kpis.json"
        )
        if not payload_path.exists():
            raise CommandError(f"Seed file not found: {payload_path}")

        try:
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {payload_path}: {exc}") from exc

        if not isinstance(payload, list):
            raise CommandError("canonical_kpis.json must contain a top-level array.")
        return payload

    def _seed_org(self, org: Organization, payload: list[dict[str, Any]]) -> dict[str, int]:
        counts = {
            "created": 0,
            "updated": 0,
            "role_warnings": 0,
            "role_fallbacks": 0,
            "user_warnings": 0,
        }

        category_choices = {value for value, _ in KpiDefinition.Category.choices}
        unit_choices = {value for value, _ in KpiDefinition.Unit.choices}
        direction_choices = {value for value, _ in KpiDefinition.Direction.choices}
        frequency_choices = {value for value, _ in KpiDefinition.Frequency.choices}
        grain_choices = {value for value, _ in KpiDefinition.Grain.choices}

        with transaction.atomic():
            for entry in payload:
                code = str((entry or {}).get("code", "")).strip().upper()
                if not code:
                    raise CommandError("Each KPI entry must include a non-empty code.")

                name = str((entry or {}).get("name", "")).strip()
                if not name:
                    raise CommandError(f"KPI '{code}' is missing required field 'name'.")

                category = self._validate_choice(
                    entry,
                    "category",
                    category_choices,
                    code,
                )
                unit = self._validate_choice(entry, "unit", unit_choices, code)
                direction = self._validate_choice(
                    entry,
                    "direction",
                    direction_choices,
                    code,
                )
                frequency = self._validate_choice(
                    entry,
                    "frequency",
                    frequency_choices,
                    code,
                )
                grain = self._validate_choice(entry, "grain", grain_choices, code)

                dimensions = entry.get("dimensions", [])
                if not isinstance(dimensions, list):
                    raise CommandError(f"KPI '{code}' has non-list dimensions.")
                dimensions = [str(d).strip() for d in dimensions if str(d).strip()]

                owner_role_slug = str((entry or {}).get("owner_role_slug", "")).strip()
                owner_role, used_fallback = self._resolve_owner_role(
                    org=org,
                    category=category,
                    preferred_slug=owner_role_slug,
                )
                if owner_role is None:
                    counts["role_warnings"] += 1
                elif used_fallback:
                    counts["role_fallbacks"] += 1

                owner_user = None
                owner_user_email = str((entry or {}).get("owner_user_email", "")).strip()
                if owner_user_email:
                    owner_user = User.objects.filter(
                        email__iexact=owner_user_email,
                        profile__organization=org,
                    ).first()
                    if owner_user is None:
                        counts["user_warnings"] += 1

                defaults = {
                    "name": name,
                    "description": str((entry or {}).get("description", "")).strip(),
                    "category": category,
                    "unit": unit,
                    "direction": direction,
                    "frequency": frequency,
                    "is_canonical": bool((entry or {}).get("is_canonical", True)),
                    "grain": grain,
                    "dimensions": dimensions,
                    "owner_role": owner_role,
                    "owner_user": owner_user,
                    "freshness_sla_minutes": self._to_int(
                        entry.get("freshness_sla_minutes", 1440),
                        "freshness_sla_minutes",
                        code,
                    ),
                    "formula_expression": str(
                        (entry or {}).get("formula_expression", "")
                    ).strip(),
                    "data_source": str(
                        (entry or {}).get("data_source", "Metrics contract seed")
                    ).strip(),
                    "green_threshold": self._to_decimal(
                        entry.get("green_threshold"),
                        "green_threshold",
                        code,
                    ),
                    "amber_threshold": self._to_decimal(
                        entry.get("amber_threshold"),
                        "amber_threshold",
                        code,
                    ),
                    "bonus_green_pct": self._to_optional_decimal(
                        entry.get("bonus_green_pct"),
                        "bonus_green_pct",
                        code,
                    ),
                    "bonus_amber_pct": self._to_optional_decimal(
                        entry.get("bonus_amber_pct"),
                        "bonus_amber_pct",
                        code,
                    ),
                    "bonus_red_pct": self._to_optional_decimal(
                        entry.get("bonus_red_pct"),
                        "bonus_red_pct",
                        code,
                    ),
                    "is_active": bool((entry or {}).get("is_active", True)),
                    "is_system": bool((entry or {}).get("is_system", True)),
                    "sort_order": self._to_int(entry.get("sort_order", 0), "sort_order", code),
                }

                _, created = KpiDefinition.objects.update_or_create(
                    organization=org,
                    code=code,
                    defaults=defaults,
                )
                if created:
                    counts["created"] += 1
                else:
                    counts["updated"] += 1

        return counts

    def _resolve_owner_role(
        self,
        *,
        org: Organization,
        category: str,
        preferred_slug: str,
    ):
        roles = Role.objects.filter(organization=org)
        if preferred_slug:
            direct = roles.filter(slug=preferred_slug).first()
            if direct is not None:
                return direct, False

        category_keywords = {
            "finance": ("finance", "account"),
            "hr": ("hr", "human", "people"),
            "project_management": ("project", "pm"),
            "sales": ("sales", "crm", "business"),
            "operations": ("operations", "support", "service", "ops"),
            "property": ("property", "estate", "asset"),
            "procurement": ("procurement", "sourcing", "supply"),
            "quality": ("quality", "qa"),
            "safety": ("safety", "hse"),
            "compliance": ("compliance", "risk", "legal"),
            "construction": ("construction", "site", "engineering"),
        }
        for keyword in category_keywords.get(category, ()):
            match = roles.filter(
                Q(name__icontains=keyword) | Q(slug__icontains=keyword)
            ).order_by("-is_system", "name").first()
            if match is not None:
                return match, True

        fallback = roles.filter(
            Q(name__icontains="admin") | Q(slug__icontains="admin")
        ).order_by("-is_system", "name").first()
        if fallback is not None:
            return fallback, True

        fallback = roles.order_by("-is_system", "name").first()
        if fallback is not None:
            return fallback, True
        return None, False

    def _validate_choice(
        self,
        entry: dict[str, Any],
        field: str,
        choices: set[str],
        code: str,
    ) -> str:
        value = str((entry or {}).get(field, "")).strip()
        if not value:
            raise CommandError(f"KPI '{code}' is missing required field '{field}'.")
        if value not in choices:
            raise CommandError(
                f"KPI '{code}' has invalid {field}='{value}'. Allowed: {sorted(choices)}"
            )
        return value

    def _to_decimal(self, value: Any, field: str, code: str) -> Decimal:
        if value in (None, ""):
            raise CommandError(f"KPI '{code}' is missing required field '{field}'.")
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise CommandError(
                f"KPI '{code}' has invalid decimal for {field}: {value!r}"
            ) from exc

    def _to_optional_decimal(self, value: Any, field: str, code: str):
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise CommandError(
                f"KPI '{code}' has invalid decimal for {field}: {value!r}"
            ) from exc

    def _to_int(self, value: Any, field: str, code: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise CommandError(
                f"KPI '{code}' has invalid integer for {field}: {value!r}"
            ) from exc
        if parsed < 0:
            raise CommandError(f"KPI '{code}' has negative value for {field}.")
        return parsed
