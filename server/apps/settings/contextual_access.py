from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import time
from typing import Any

from django.db.models import Prefetch, Q
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone

from .models import AccessPolicy, PolicyAction, PolicyCondition


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str = ""


def evaluate_contextual_access(
    *,
    user,
    request,
    module: str,
    sub_module: str,
    action: str,
) -> AccessDecision:
    if not user or not getattr(user, "is_authenticated", False):
        return AccessDecision(False, "Authentication is required.")

    if getattr(user, "is_superuser", False):
        return AccessDecision(True)

    profile = getattr(user, "profile", None)
    organization = getattr(profile, "organization", None)
    if organization is None:
        return AccessDecision(False, "User organization context is missing.")

    try:
        policies = list(
            AccessPolicy.objects.filter(
                organization=organization,
                is_active=True,
            )
            .filter(
                Q(module="") | Q(module=module),
                Q(sub_module="") | Q(sub_module=sub_module),
                Q(action="") | Q(action=action),
            )
            .prefetch_related(
                Prefetch(
                    "conditions",
                    queryset=PolicyCondition.objects.filter(is_active=True).order_by(
                        "sort_order", "id"
                    ),
                ),
                Prefetch(
                    "policy_actions",
                    queryset=PolicyAction.objects.filter(is_active=True).order_by(
                        "sort_order", "id"
                    ),
                ),
            )
            .order_by("priority", "id")
        )
    except (ProgrammingError, OperationalError):
        return AccessDecision(True)

    if not policies:
        return AccessDecision(True)

    context = _build_context(
        user=user,
        request=request,
        organization=organization,
        module=module,
        sub_module=sub_module,
        action=action,
    )

    for policy in policies:
        if not _policy_matches(policy, context):
            continue
        decision = _apply_policy_actions(policy, context)
        if not decision.allowed:
            return decision

    return AccessDecision(True)


def _build_context(*, user, request, organization, module: str, sub_module: str, action: str) -> dict[str, Any]:
    profile = getattr(user, "profile", None)
    assigned_role = getattr(profile, "assigned_role", None)
    role_slug = getattr(assigned_role, "slug", "") if assigned_role else ""

    now_local = timezone.localtime(timezone.now()).time()

    return {
        "organization": organization,
        "module": module,
        "sub_module": sub_module,
        "action": action,
        "role_slug": role_slug,
        "profile_role": getattr(profile, "role", ""),
        "source_ip": _client_ip_from_request(request),
        "country_code": _country_code_from_request(request),
        "device_trusted": _is_device_trusted(request),
        "mfa_enabled": bool(getattr(profile, "mfa_enabled", False)),
        "current_time": now_local,
    }


def _policy_matches(policy: AccessPolicy, context: dict[str, Any]) -> bool:
    conditions = list(policy.conditions.all())
    if not conditions:
        return True
    return all(_condition_matches(condition, context) for condition in conditions)


def _condition_matches(condition: PolicyCondition, context: dict[str, Any]) -> bool:
    condition_type = condition.condition_type
    operator = condition.operator
    expected = condition.value

    if condition_type == PolicyCondition.ConditionType.USER_ROLE:
        role_slug = context.get("role_slug")
        profile_role = context.get("profile_role")
        actual = role_slug or profile_role
        return _compare(actual, operator, expected)

    if condition_type == PolicyCondition.ConditionType.ACTION:
        return _compare(context.get("action"), operator, expected)

    if condition_type == PolicyCondition.ConditionType.IP_RESTRICTION:
        ip_value = context.get("source_ip")
        if operator == PolicyCondition.Operator.CIDR:
            return _ip_in_any_cidr(ip_value, _to_list(expected))
        return _compare(ip_value, operator, expected)

    if condition_type == PolicyCondition.ConditionType.TIME_RESTRICTION:
        return _time_in_window(context.get("current_time"), expected)

    if condition_type == PolicyCondition.ConditionType.DEVICE_RESTRICTION:
        return _compare(context.get("device_trusted"), operator, expected)

    if condition_type == PolicyCondition.ConditionType.MFA_REQUIREMENT:
        return _compare(context.get("mfa_enabled"), operator, expected)

    if condition_type == PolicyCondition.ConditionType.LOCATION:
        actual_country = (context.get("country_code") or "").upper()
        return _compare(actual_country, operator, expected)

    return False


def _apply_policy_actions(policy: AccessPolicy, context: dict[str, Any]) -> AccessDecision:
    actions = list(policy.policy_actions.all())
    if not actions:
        return AccessDecision(True)

    for policy_action in actions:
        action_type = policy_action.action_type
        params = policy_action.parameters or {}

        if action_type == PolicyAction.ActionType.ALLOW:
            continue

        if action_type == PolicyAction.ActionType.DENY:
            return AccessDecision(
                False,
                policy_action.message or "Access denied by policy.",
            )

        if action_type == PolicyAction.ActionType.REQUIRE_MFA:
            if not context.get("mfa_enabled"):
                return AccessDecision(
                    False,
                    policy_action.message
                    or "MFA is required for this action.",
                )
            continue

        if action_type == PolicyAction.ActionType.REQUIRE_CORPORATE_DEVICE:
            if not context.get("device_trusted"):
                return AccessDecision(
                    False,
                    policy_action.message
                    or "A corporate/trusted device is required for this action.",
                )
            continue

        if action_type == PolicyAction.ActionType.REQUIRE_OFFICE_IP:
            cidrs = _to_list(params.get("cidrs"))
            if not _ip_in_any_cidr(context.get("source_ip"), cidrs):
                return AccessDecision(
                    False,
                    policy_action.message
                    or "This action is restricted to approved office networks.",
                )
            continue

    return AccessDecision(True)


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == PolicyCondition.Operator.EQ:
        return actual == _normalize_expected(expected)
    if operator == PolicyCondition.Operator.NEQ:
        return actual != _normalize_expected(expected)
    if operator == PolicyCondition.Operator.IN:
        return actual in _to_list(expected)
    if operator == PolicyCondition.Operator.NOT_IN:
        return actual not in _to_list(expected)
    if operator == PolicyCondition.Operator.GTE:
        actual_num, expected_num = _to_float(actual), _to_float(expected)
        return actual_num is not None and expected_num is not None and actual_num >= expected_num
    if operator == PolicyCondition.Operator.LTE:
        actual_num, expected_num = _to_float(actual), _to_float(expected)
        return actual_num is not None and expected_num is not None and actual_num <= expected_num
    if operator == PolicyCondition.Operator.BETWEEN:
        bounds = _to_list(expected)
        if len(bounds) != 2:
            return False
        actual_num, low, high = _to_float(actual), _to_float(bounds[0]), _to_float(bounds[1])
        return (
            actual_num is not None
            and low is not None
            and high is not None
            and low <= actual_num <= high
        )
    if operator == PolicyCondition.Operator.CIDR:
        return _ip_in_any_cidr(str(actual) if actual is not None else None, _to_list(expected))
    return False


def _normalize_expected(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _to_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _time_in_window(current: time | None, expected: Any) -> bool:
    if current is None or not isinstance(expected, dict):
        return False

    start_raw = expected.get("start")
    end_raw = expected.get("end")
    start = _parse_hhmm(start_raw)
    end = _parse_hhmm(end_raw)
    if start is None or end is None:
        return False

    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


def _parse_hhmm(value: Any) -> time | None:
    if not isinstance(value, str) or ":" not in value:
        return None
    parts = value.split(":", 1)
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return time(hour=hour, minute=minute)


def _ip_in_any_cidr(ip_value: str | None, cidrs: list[Any]) -> bool:
    if not ip_value or not cidrs:
        return False

    try:
        ip_obj = ipaddress.ip_address(ip_value)
    except ValueError:
        return False

    for entry in cidrs:
        try:
            network = ipaddress.ip_network(str(entry), strict=False)
        except ValueError:
            continue
        if ip_obj in network:
            return True
    return False


def _client_ip_from_request(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _country_code_from_request(request) -> str:
    if request is None:
        return ""
    direct = request.headers.get("X-Country-Code", "")
    if direct:
        return str(direct).strip().upper()
    cloudflare = request.headers.get("CF-IPCountry", "")
    return str(cloudflare).strip().upper()


def _is_device_trusted(request) -> bool:
    if request is None:
        return False
    header_value = (
        request.headers.get("X-Device-Trusted")
        or request.headers.get("X-Corporate-Device")
        or ""
    )
    return str(header_value).strip().lower() in {"1", "true", "yes", "y", "on"}
