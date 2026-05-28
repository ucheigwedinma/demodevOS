from __future__ import annotations

from apps.accounts.api_test_skeleton_utils import APISkeletonBaseTestCase, build_todo_test

SUPPORT_DESK_CASES = [
    ("SD-001", "Overview metrics aggregate by status and priority"),
    ("SD-002", "Ticket queue list filters and pagination"),
    ("SD-003", "Request queue uses request-category ticket scope"),
    ("SD-004", "Knowledge base article CRUD and publication workflow"),
    ("SD-005", "Knowledge base feedback and view tracking"),
    ("SD-006", "SLA policy CRUD and activation toggle"),
    ("SD-007", "SLA escalations overview breached/upcoming metrics"),
    ("SD-008", "SLA escalation queue filters by breached and escalated"),
    ("SD-009", "Communication log CRUD tracks channel/direction and ticket linkage"),
    ("SD-010", "Communication overview aggregates interactions by type and channel"),
    ("SD-011", "WhatsApp communication endpoint records outbound integration events"),
    ("SD-012", "Automation rule CRUD with trigger/conditions/actions validation"),
    ("SD-013", "Automation engine executes on ticket create/update/status/SLA triggers"),
    ("SD-014", "Automation overview and run history endpoints expose execution telemetry"),
]


class SupportDeskApiSkeletonTests(APISkeletonBaseTestCase):
    """Skeletons for support desk API coverage."""


for _case_id, _title in SUPPORT_DESK_CASES:
    _name, _fn = build_todo_test(_case_id, _title)
    setattr(SupportDeskApiSkeletonTests, _name, _fn)
