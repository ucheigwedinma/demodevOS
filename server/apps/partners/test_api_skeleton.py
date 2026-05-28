from __future__ import annotations

from apps.accounts.api_test_skeleton_utils import (
    APISkeletonBaseTestCase,
    build_todo_test,
)

PARTNER_CASES = [
    ("PART-001", "Create onboarding case per partner type"),
    ("PART-002", "Stage progression and SLA tracking"),
    ("PART-003", "Submit case for review gate"),
    ("PART-004", "ERP entity creation from approved case"),
    ("PART-005", "Entitlement provisioning"),
    ("PART-006", "Grant portal access eligibility checks"),
    ("PART-007", "Approval recording with role labels"),
    ("PART-008", "Audit timeline event completeness"),
    ("PART-009", "Source lead linkage and archival behavior"),
    ("PART-010", "Partner type specific module rendering"),
    ("PART-011", "Data partitioning by project SPV contract"),
    ("PART-012", "Portal legal acceptance capture"),
    ("PART-013", "Notifications for case milestones"),
    ("PART-014", "Search filter in partner case list"),
    ("PART-015", "Partner cannot elevate own entitlements"),
]


class PartnerPortalApiSkeletonTests(APISkeletonBaseTestCase):
    """Skeletons for partner-agnostic portal API coverage."""


for _case_id, _title in PARTNER_CASES:
    _name, _fn = build_todo_test(_case_id, _title)
    setattr(PartnerPortalApiSkeletonTests, _name, _fn)

