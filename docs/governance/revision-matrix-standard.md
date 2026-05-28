# Revision Matrix Standard

Version: v1.0  
Status: Active  
Owner: Document Control Office

## Purpose
Define how document revisions are represented, controlled, and approved in the centralized repository.

## Revision Model

- Revision marker in document number: `R<n>`
- Revision source of truth: `Document.revision_number`
- Version record: `DocumentVersion(version_major, version_minor)`

## Mapping Rules

- `Document.revision_number` maps to `DocumentVersion.version_major`
- Document number revision segment always reflects current revision number:
  - `R0` = initial controlled release
  - `R1` = first revision
  - `R2` = second revision

## Version Numbering Convention

- Major revision: structural/commercial/regulatory impact (`v2.0`, `v3.0`)
- Minor revision: typo/clarification/non-material update (`v2.1`, `v2.2`)

## Approval Matrix

| Stage | Version State | Approval Status | Required Decision |
|---|---|---|---|
| Draft Upload | `vN.M` created | `pending` | Await role-based review |
| Review Complete | Reviewer submits decision | `approved` / `rejected` | Finalized for that cycle |
| Publish | Current version pointer updated | `approved` | Document revision becomes active |

## Decision Codes

- `approved`: revision accepted and eligible for active use
- `rejected`: revision rejected; update required before re-submission

## Control Rules

1. Each `(document, version_major, version_minor)` must be unique.
2. Each approver can issue one decision per document version.
3. When a higher/equal version is accepted as current, document revision updates accordingly.
4. Revision history is append-only through `DocumentVersion` records.

## Operational Examples

- Initial issue: `LUA-PH2-REG-004-R0` with `v0.0`
- First approved revision: `LUA-PH2-REG-004-R1` with `v1.0`
- Minor update: remains `R1` if major unchanged and current major is still `1`
- Next major revision: `LUA-PH2-REG-004-R2` with `v2.0`
