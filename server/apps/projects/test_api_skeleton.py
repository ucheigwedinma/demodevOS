from __future__ import annotations

from apps.accounts.api_test_skeleton_utils import APISkeletonBaseTestCase, build_todo_test

PROJECT_CASES = [
    ("PROJ-001", "Create project and default phases"),
    ("PROJ-002", "Add milestone with gate requirements"),
    ("PROJ-003", "Task assignment and comment flow"),
    ("PROJ-004", "Risk register CRUD"),
    ("PROJ-005", "Variation order lifecycle"),
    ("PROJ-006", "Field operation report submission"),
    ("PROJ-007", "Stage-gate enforcement blocks completion"),
    ("PROJ-008", "Budget vs cost linkage to finance"),
    ("PROJ-009", "Project list scope filtering"),
    ("PROJ-010", "Project templates apply consistently"),
]


class ProjectsApiSkeletonTests(APISkeletonBaseTestCase):
    """Skeletons for projects module API coverage."""


for _case_id, _title in PROJECT_CASES:
    _name, _fn = build_todo_test(_case_id, _title)
    setattr(ProjectsApiSkeletonTests, _name, _fn)

