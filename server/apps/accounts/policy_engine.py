"""Access-policy evaluation engine.

Reads ``apps.settings.AccessPolicy`` rows + their ``PolicyCondition``
and ``PolicyAction`` children, evaluates them against the current
request context, and returns a Decision.

Design points worth knowing:

  * **Fail-open.** Any unhandled exception inside a condition handler
    causes that policy to be SKIPPED, not denied. Logging captures the
    failure; the request proceeds as if the policy had matched
    everything else. This is intentional — buggy policies must not
    lock everyone out.

  * **First-match wins.** Policies are evaluated in priority order
    (ascending) plus created_at as a tiebreaker. The first policy
    whose conditions ALL match returns its action. Subsequent
    policies are not evaluated.

  * **Default decision is ALLOW.** No policies, all conditions
    skipped, or no policy matched → request proceeds. Operators must
    add an explicit deny policy if they want default-deny.

The middleware (apps.accounts.policy_middleware.AccessPolicyMiddleware)
is the integration point — it calls ``evaluate_request`` once per
authenticated request and converts the Decision into an HTTP response
(403 for deny, 403 with code for step_up_mfa, header for warn).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from ipaddress import ip_address, ip_network
from typing import Iterable, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """Result of evaluating a request against the policy set."""
    action: str = "allow"           # allow | deny | step_up_mfa | warn
    matched_policy_id: Optional[int] = None
    matched_policy_name: str = ""
    message: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def blocks(self) -> bool:
        return self.action in ("deny", "step_up_mfa")


# ── Audience matching ────────────────────────────────────────────────


def _user_matches_audience(user, applies_to: dict) -> bool:
    """Empty applies_to = matches everyone. Otherwise the user must
    appear in user_ids OR have one of the role_ids assigned."""
    if not applies_to:
        return True
    role_ids = applies_to.get("role_ids") or []
    user_ids = applies_to.get("user_ids") or []
    if not role_ids and not user_ids:
        return True
    if user_ids and user.id in user_ids:
        return True
    if role_ids:
        profile = getattr(user, "profile", None)
        if profile and profile.assigned_role_id in role_ids:
            return True
    return False


# ── Condition handlers ───────────────────────────────────────────────


def _check_ip_restriction(condition, request) -> bool:
    """Match if request IP is in CIDR list (allowlist semantics)."""
    cidrs = condition.value.get("cidrs") or []
    if not cidrs:
        return True  # no list = no restriction = matches
    ip_str = _client_ip(request)
    if not ip_str:
        return False
    try:
        ip = ip_address(ip_str)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            if ip in ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def _check_time_restriction(condition, request) -> bool:
    """Match if current time is within allowed window."""
    val = condition.value or {}
    tz_name = val.get("timezone") or "UTC"
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = None

    now = timezone.now()
    if tz:
        now = now.astimezone(tz)

    weekdays = val.get("allowed_weekdays")
    if weekdays is not None and now.weekday() not in weekdays:
        return False

    start_h = val.get("start_hour")
    end_h = val.get("end_hour")
    if start_h is not None and end_h is not None:
        try:
            start = dt_time(hour=int(start_h))
            end = dt_time(hour=int(end_h))
        except (ValueError, TypeError):
            return True
        cur = now.time()
        if start <= end:
            if not (start <= cur <= end):
                return False
        else:
            # Window crosses midnight (e.g. 22..6)
            if not (cur >= start or cur <= end):
                return False
    return True


def _check_location_restriction(condition, request) -> bool:
    """Match if request country is in allowed list (or NOT in blocked).

    Country detection is best-effort — we read a CF-IPCountry / X-Country
    header if upstream sets one. Without that header, this returns True
    (no opinion) so policies don't lock out organisations without
    geo-IP middleware.
    """
    val = condition.value or {}
    country = (
        request.META.get("HTTP_CF_IPCOUNTRY")
        or request.META.get("HTTP_X_COUNTRY")
        or ""
    ).upper()
    allow = [c.upper() for c in (val.get("allowed_countries") or [])]
    deny = [c.upper() for c in (val.get("denied_countries") or [])]
    if not country:
        return True  # cannot determine; don't block
    if deny and country in deny:
        return False
    if allow and country not in allow:
        return False
    return True


def _check_device_restriction(condition, request) -> bool:
    """Match if user agent fits the device policy."""
    val = condition.value or {}
    ua = (request.META.get("HTTP_USER_AGENT") or "").lower()
    blocked = [s.lower() for s in (val.get("blocked_user_agents") or [])]
    if any(b in ua for b in blocked):
        return False
    required = [s.lower() for s in (val.get("required_substrings") or [])]
    if required and not any(r in ua for r in required):
        return False
    return True


def _check_mfa_requirement(condition, request) -> bool:
    """Match if the request session reports MFA verified."""
    val = condition.value or {}
    if not val.get("required"):
        return True
    auth = getattr(request, "successful_authenticator", None)
    if auth and hasattr(auth, "get_validated_token"):
        try:
            token = getattr(request, "auth", None)
            if token and bool(token.get("mfa")):
                return True
        except Exception:
            pass
    profile = getattr(getattr(request, "user", None), "profile", None)
    return bool(profile and profile.mfa_enabled)


def _check_user_role(condition, request) -> bool:
    """Match if user's assigned_role is in the listed role IDs."""
    val = condition.value or {}
    role_ids = val.get("role_ids") or []
    if not role_ids:
        return True
    profile = getattr(getattr(request, "user", None), "profile", None)
    return bool(profile and profile.assigned_role_id in role_ids)


_CONDITION_HANDLERS = {
    "ip_restriction": _check_ip_restriction,
    "time_restriction": _check_time_restriction,
    "location": _check_location_restriction,
    "device_restriction": _check_device_restriction,
    "mfa_requirement": _check_mfa_requirement,
    "user_role": _check_user_role,
}


# ── Action mapping ───────────────────────────────────────────────────


_ACTION_TO_DECISION = {
    "allow": "allow",
    "deny": "deny",
    "require_mfa": "step_up_mfa",
    "require_office_ip": "deny",      # if user isn't on office IP, the IP-restriction condition would have failed
    "require_corporate_device": "deny",
}


# ── Top-level evaluator ──────────────────────────────────────────────


def _client_ip(request) -> str:
    """Best-effort client IP extraction. Honours X-Forwarded-For when the
    middleware in front of Django is trusted."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def evaluate_request(request) -> Decision:
    """Evaluate the active policy set against this request.

    Returns a Decision. Default action is ``allow`` if no policy
    matches. Skips evaluation for unauthenticated requests (let the
    auth layer reject those) and for users with no profile/org."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return Decision()

    profile = getattr(user, "profile", None)
    org = getattr(profile, "organization", None) if profile else None
    if not org:
        return Decision()

    # Lazy import to avoid circular at module load
    from apps.settings.models import AccessPolicy

    policies = (
        AccessPolicy.objects
        .filter(organization=org, is_active=True)
        .prefetch_related("conditions", "policy_actions")
        .order_by("priority", "created_at")
    )

    for policy in policies:
        try:
            # Audience filter: stored on the AccessPolicy as
            # module/sub_module/action OR derived. For now, we treat
            # AccessPolicy as applying to all users within the org;
            # role-targeting can use a user_role condition.
            all_match = True
            for cond in policy.conditions.all():
                if not cond.is_active:
                    continue
                handler = _CONDITION_HANDLERS.get(cond.condition_type)
                if not handler:
                    continue
                if not handler(cond, request):
                    all_match = False
                    break
            if not all_match:
                continue

            # First active action wins
            action_row = next(
                (a for a in policy.policy_actions.all() if a.is_active),
                None,
            )
            decision_action = "allow"
            message = ""
            if action_row:
                decision_action = _ACTION_TO_DECISION.get(action_row.action_type, "allow")
                message = action_row.message or ""

            decision = Decision(
                action=decision_action,
                matched_policy_id=policy.id,
                matched_policy_name=policy.name,
                message=message,
                metadata={"policy_kind": policy.kind, "priority": policy.priority},
            )

            # Allow lets later policies still evaluate? In this engine,
            # first-match wins — including allow. If you need
            # "allow-and-continue" semantics, add a flag on PolicyAction.
            return decision

        except Exception:
            logger.exception("policy_engine: skipping policy id=%s due to error", policy.id)
            continue

    return Decision()  # default allow
