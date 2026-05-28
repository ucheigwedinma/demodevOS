"""
Custom password validators.

Two layers:

  1. Static validators (UppercaseValidator, LowercaseValidator,
     SpecialCharacterValidator, MaxLengthValidator) — fixed-policy
     checks unaffected by per-org config. Used during registration
     before a user/org is established.

  2. Policy-aware validators (OrganizationPasswordPolicyValidator,
     PasswordHistoryValidator) — read the user's Organization to apply
     per-org rules (min length, complexity flags, reuse prevention).
     Active when a user is passed to validate(); silently no-ops
     otherwise so registration-time runs aren't broken.

The static layer always runs (set in AUTH_PASSWORD_VALIDATORS); the
policy-aware layer kicks in when a user is passed (set_password +
ChangePasswordSerializer flows).
"""

import re

from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class UppercaseValidator:
    """Require at least one uppercase letter."""

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code="password_no_uppercase",
            )

    def get_help_text(self):
        return _("Your password must contain at least one uppercase letter.")


class LowercaseValidator:
    """Require at least one lowercase letter."""

    def validate(self, password, user=None):
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code="password_no_lowercase",
            )

    def get_help_text(self):
        return _("Your password must contain at least one lowercase letter.")


class SpecialCharacterValidator:
    """Require at least one special (non-alphanumeric) character."""

    def validate(self, password, user=None):
        if not re.search(r"[^A-Za-z0-9]", password):
            raise ValidationError(
                _("Password must contain at least one special character (e.g. !@#$%^&*)."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _("Your password must contain at least one special character (e.g. !@#$%^&*).")


class MaxLengthValidator:
    """
    Reject passwords longer than max_length characters.

    Extremely long passwords can cause denial-of-service when hashed with
    memory-hard algorithms like Argon2. NIST SP 800-63B recommends allowing
    at least 64 characters; we default to 128 for generous usability while
    still bounding the hashing cost.
    """

    def __init__(self, max_length=128):
        self.max_length = max_length

    def validate(self, password, user=None):
        if len(password) > self.max_length:
            raise ValidationError(
                _("Password must be at most %(max_length)d characters."),
                code="password_too_long",
                params={"max_length": self.max_length},
            )

    def get_help_text(self):
        return _("Your password must be at most %(max_length)d characters.") % {
            "max_length": self.max_length,
        }


# ── Policy-aware validators (read from user.profile.organization) ───


def _user_org_policy(user):
    """Return the policy dict from user's organization, or None if no
    user/profile/org is available (e.g. registration before user exists,
    or anonymous calls)."""
    if user is None:
        return None
    profile = getattr(user, "profile", None)
    org = getattr(profile, "organization", None) if profile else None
    if org is None:
        return None
    return {
        "min_length": int(org.password_min_length),
        "require_uppercase": bool(org.password_require_uppercase),
        "require_digits": bool(org.password_require_digits),
        "require_special": bool(org.password_require_special),
        "history_count": int(org.password_history_count),
    }


class OrganizationPasswordPolicyValidator:
    """Apply the user's Organization password policy.

    Covers: min_length, require_uppercase, require_digits,
    require_special. No-op when no user (registration falls back to
    the static validators above).
    """

    def validate(self, password, user=None):
        policy = _user_org_policy(user)
        if not policy:
            return
        errors = []
        if len(password) < policy["min_length"]:
            errors.append(
                ValidationError(
                    _("Your organisation requires passwords to be at least %(n)d characters."),
                    code="password_too_short",
                    params={"n": policy["min_length"]},
                )
            )
        if policy["require_uppercase"] and not re.search(r"[A-Z]", password):
            errors.append(
                ValidationError(
                    _("Your organisation requires at least one uppercase letter."),
                    code="org_password_no_uppercase",
                )
            )
        if policy["require_digits"] and not re.search(r"\d", password):
            errors.append(
                ValidationError(
                    _("Your organisation requires at least one digit."),
                    code="org_password_no_digits",
                )
            )
        if policy["require_special"] and not re.search(r"[^A-Za-z0-9]", password):
            errors.append(
                ValidationError(
                    _("Your organisation requires at least one special character."),
                    code="org_password_no_special",
                )
            )
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Your password must comply with your organisation's password policy "
            "(see /iam/auth)."
        )


class PasswordHistoryValidator:
    """Reject passwords that match any of the user's last N hashes.

    N comes from Organization.password_history_count (0 = no check).
    History is recorded by ChangePasswordSerializer / set_password
    helpers — see apps.accounts.security.record_password_change.
    """

    def validate(self, password, user=None):
        policy = _user_org_policy(user)
        if not policy:
            return
        n = policy["history_count"]
        if n <= 0 or user is None or not user.pk:
            return
        # Lazy import to avoid circular at module load
        from apps.accounts.models import UserPasswordHistory
        recent = UserPasswordHistory.objects.filter(user=user).order_by("-changed_at")[:n]
        for entry in recent:
            try:
                if check_password(password, entry.password_hash):
                    raise ValidationError(
                        _("This password matches one of your last %(n)d passwords. Choose a different one."),
                        code="password_recent_reuse",
                        params={"n": n},
                    )
            except ValueError:
                # Malformed/legacy hash — skip rather than break the flow
                continue

    def get_help_text(self):
        return _(
            "Your password must not match any of your most recent passwords."
        )
