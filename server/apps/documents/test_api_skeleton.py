from __future__ import annotations

from apps.accounts.api_test_skeleton_utils import (
    APISkeletonBaseTestCase,
    build_todo_test,
)

DOCUMENT_CASES = [
    ("DOC-001", "Upload document and create initial version"),
    ("DOC-002", "Upload new version with audit continuity"),
    ("DOC-003", "Confidentiality label enforcement"),
    ("DOC-004", "Submit document workflow and decision"),
    ("DOC-005", "Digital signature request lifecycle"),
    ("DOC-006", "OCR extraction job output shape"),
    ("DOC-007", "Retention expiry monitor behavior"),
    ("DOC-008", "Full-text search relevance and permissions"),
    ("DOC-009", "Download share events audited with IP"),
    ("DOC-010", "Archive supersede delete policy enforcement"),
]


class DocumentsApiSkeletonTests(APISkeletonBaseTestCase):
    """Skeletons for document and governance API coverage."""


for _case_id, _title in DOCUMENT_CASES:
    _name, _fn = build_todo_test(_case_id, _title)
    setattr(DocumentsApiSkeletonTests, _name, _fn)

