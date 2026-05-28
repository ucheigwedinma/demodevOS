# Approval Template Builder (Phase 5)

The template builder defines reusable approval chains and routing rules.

## Data Model

### Template

`documents_documentworkflowtemplate`

- `code`
- `name`
- `description`
- `is_default`
- `is_active`

### Template Steps

`documents_documentworkflowtemplatestep`

- `template_id`
- `sequence`
- `approver_label` (e.g., Legal, Finance, COO)
- `approver_role_slug` (optional strict role gate)
- `is_active`

### Routing Rules

`documents_documentworkflowrule`

- `template_id`
- `document_type_id` (optional)
- `min_contract_value` / `max_contract_value` (optional)
- `allowed_confidentiality_levels`
- `allowed_project_risk_ratings`
- `priority`
- `is_active`

## Example Conditional Rule

If:

- `document_type = Contract`
- `contract_value > 100000`

Route:

- `Legal -> Finance -> COO`

## API Endpoints

- `GET/POST/PATCH/DELETE /api/documents/control/workflow/templates/`
- `GET/POST/PATCH/DELETE /api/documents/control/workflow/template-steps/`
- `GET/POST/PATCH/DELETE /api/documents/control/workflow/rules/`

## Seed Command

A default setup is provided via:

```bash
python3 manage.py seed_documents_phase5_workflows --reset
```

This seeds:

- Default fallback template (`default-document-approval`)
- High-value contract template (`high-value-contract-approval`)
- Rule: `Contract > 100k -> Legal -> Finance -> COO` (if Document Type exists)
