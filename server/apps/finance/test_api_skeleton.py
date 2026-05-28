from __future__ import annotations

from apps.accounts.api_test_skeleton_utils import (
    APISkeletonBaseTestCase,
    build_todo_test,
)

FINANCE_CASES = [
    ("FIN-001", "Create bill with valid line items"),
    ("FIN-002", "Bill total recalculates after line update delete"),
    ("FIN-003", "Submit bill for approval creates workflow instance"),
    ("FIN-004", "Duplicate active workflow submission blocked"),
    ("FIN-005", "Invoice create edit delete permissions"),
    ("FIN-006", "Budget create and approval flow"),
    ("FIN-007", "Journal posting validates balancing entries"),
    ("FIN-008", "Payments update related balances"),
    ("FIN-009", "Trial balance report correctness"),
    ("FIN-010", "General ledger filter correctness"),
    ("FIN-011", "SPV entity creation and linking"),
    ("FIN-012", "Payment plan installment schedule integrity"),
    ("FIN-013", "Customer CRUD with role restrictions"),
    ("FIN-014", "Investor records and project investor linking"),
    ("FIN-015", "Export endpoints security and data correctness"),
    ("FIN-016", "Finance dashboard endpoints availability"),
    ("FIN-017", "Contextual policy on finance approve action"),
    ("FIN-018", "Large dataset pagination correctness"),
]


class FinanceApiSkeletonTests(APISkeletonBaseTestCase):
    """Skeletons for finance module API coverage."""


for _case_id, _title in FINANCE_CASES:
    _name, _fn = build_todo_test(_case_id, _title)
    setattr(FinanceApiSkeletonTests, _name, _fn)

