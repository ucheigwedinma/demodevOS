# Workflow Configuration Engine (Phase 5)

Phase 5 introduces a dynamic, rule-driven approval engine for controlled documents.

## State Machine

Document workflow states:

- `draft`
- `submitted`
- `under_review`
- `approved`
- `rejected`
- `superseded`
- `archived`

These states are reflected on both:

- `documents_document.status`
- `documents_documentworkflowinstance.state`

## Routing Inputs

Workflow routing is resolved from:

- `document_type`
- `contract_value`
- `confidentiality_level`
- `project.risk_rating`

## Resolution Order

Rules are evaluated in ascending `priority` (lower number first).

First rule that matches all enabled conditions is selected:

- optional `document_type`
- `min_contract_value` / `max_contract_value`
- `allowed_confidentiality_levels`
- `allowed_project_risk_ratings`

If no rule matches, the active default template (`is_default=true`) is used.

## Runtime Execution

1. Submit document to workflow (`submit-workflow` action).
2. Engine resolves template and creates workflow instance + ordered steps.
3. Instance moves to `under_review`.
4. Approvers decide one step at a time in sequence.
5. Any rejection moves instance/document to `rejected`.
6. Final approval moves instance/document to `approved`.

## API Endpoints

- `POST /api/documents/control/records/{id}/submit-workflow/`
- `GET /api/documents/control/workflow/instances/`
- `GET /api/documents/control/workflow/instances/{id}/`
- `POST /api/documents/control/workflow/instances/{id}/decide/`

## Code References

- Engine: `server/apps/documents/workflow_engine.py`
- Runtime API: `server/apps/documents/views.py` (`DocumentWorkflowInstanceViewSet`)
- Models: `server/apps/documents/models.py`
