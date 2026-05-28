from __future__ import annotations

from apps.accounts.api_test_skeleton_utils import APISkeletonBaseTestCase, build_todo_test

AUTH_CASES = [
    ("AUTH-001", "Register user with valid data"),
    ("AUTH-002", "Register with duplicate email"),
    ("AUTH-003", "Register with weak password"),
    ("AUTH-004", "Login with valid credentials and MFA required"),
    ("AUTH-005", "Login with invalid password"),
    ("AUTH-006", "Login suspended user"),
    ("AUTH-007", "OTP retry limit enforcement"),
    ("AUTH-008", "Forgot password flow success"),
    ("AUTH-009", "Forgot password for unknown email"),
    ("AUTH-010", "Email verification token invalid"),
    ("AUTH-011", "OAuth login callback valid"),
    ("AUTH-012", "OAuth callback tampered state"),
    ("AUTH-013", "Turnstile protection on login/register"),
    ("AUTH-014", "Service account key creation"),
    ("AUTH-015", "Revoke API key"),
    ("AUTH-016", "Invitation acceptance with metadata"),
    ("AUTH-017", "Complete onboarding state update"),
    ("AUTH-018", "Complete tour state update"),
    ("AUTH-019", "Session with expired refresh token"),
    ("AUTH-020", "Identity status checks for all identity types"),
]


IAM_CASES = [
    ("IAM-001", "Role without permission cannot access endpoint"),
    ("IAM-014", "Unauthorized user cannot list IAM users"),
    ("IAM-015", "Privilege escalation attempt via crafted payload"),
]


class AuthApiSkeletonTests(APISkeletonBaseTestCase):
    """Skeletons for auth and identity API test coverage."""


for _case_id, _title in AUTH_CASES:
    _name, _fn = build_todo_test(_case_id, _title)
    setattr(AuthApiSkeletonTests, _name, _fn)


class IamAccountsApiSkeletonTests(APISkeletonBaseTestCase):
    """Skeletons for IAM endpoints in accounts app."""


for _case_id, _title in IAM_CASES:
    _name, _fn = build_todo_test(_case_id, _title)
    setattr(IamAccountsApiSkeletonTests, _name, _fn)

