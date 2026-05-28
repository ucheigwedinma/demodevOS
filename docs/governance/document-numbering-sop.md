# Document Numbering SOP

Version: v1.0  
Status: Active  
Owner: Document Control Office

## Purpose
Standardize document identification across land acquisition, development, sales, and handover workflows.

## Numbering Format

`[PROJECT]-[PHASE]-[CATEGORY]-[SEQUENCE]-[REV]`

Example: `LUA-PH2-REG-004-R2`

## Segment Definitions

- `PROJECT`: Project code segment (3-10 alphanumeric uppercase).  
  Example: `LUA` (Luanda Project)
- `PHASE`: Lifecycle phase code.  
  Example: `PH2`
- `CATEGORY`: Taxonomy category code.  
  Example: `REG`
- `SEQUENCE`: 3-digit sequential integer in scope.  
  Example: `004`
- `REV`: Revision marker using `R<n>`.  
  Example: `R2`

## Scope for Sequence Allocation
Sequence increments within this exact scope:

`PROJECT + PHASE + CATEGORY`

That means:
- `LUA-PH2-REG-001-R0`
- `LUA-PH2-REG-002-R0`

and separately:
- `LUA-PH2-DES-001-R0`

## System Rules

1. `document_number` is system-generated and immutable by manual free-text editing.
2. `PROJECT` segment resolves in this order:
- explicit `project_code` override on document
- derived from project name (first token, first 3 chars)
- fallback `GEN`
3. `PHASE` segment uses `DocumentWorkflowPhase.numbering_code`.
4. `CATEGORY` segment uses `DocumentType.category_code`.
5. `SEQUENCE` is zero-padded to 3 digits (`001`, `002`, ...).
6. `REV` equals current document revision number (`R0`, `R1`, ...).

## Data Governance Controls

- `PROJECT`, `PHASE`, and `CATEGORY` segments must be uppercase alphanumeric.
- Unsupported characters are stripped during normalization.
- Duplicates are blocked by uniqueness constraint on `document_number`.
- Existing records are backfilled to the standard through migration and reseed commands.

## Related Entities

- `DocumentType.category_code`
- `DocumentWorkflowPhase.numbering_code`
- `Document.sequence_number`
- `Document.revision_number`
- `Document.document_number`
