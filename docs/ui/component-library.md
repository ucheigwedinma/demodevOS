# Component Library (Phase 9)

Reusable document UI components implemented in `client/src/lib/components/documents/`.

## Components

1. `DocumentStatusBadge.svelte`
- Purpose: Render document status badge with standardized color semantics.
- Props: `status`, `small?`.

2. `DocumentKpiCard.svelte`
- Purpose: KPI metric card for repository dashboard widgets.
- Props: `title`, `value`, `subtitle?`, `accent?`.

3. `DocumentRecordsTable.svelte`
- Purpose: Reusable auto-filtered document list table.
- Props: `title`, `subtitle?`, `query?`, `pageSize?`, `emptyMessage?`, `showHeader?`, `showViewAll?`, `viewAllHref?`.

4. `DocumentMetadataPanel.svelte`
- Purpose: Document metadata block for detail pages.
- Props: `document`.

5. `DocumentLinkedEntities.svelte`
- Purpose: Render linked project/land/unit/vendor/client/business-unit entities.
- Props: `document`.

6. `DocumentVersionTimeline.svelte`
- Purpose: Timeline view of uploaded versions and approval states.
- Props: `versions`.

7. `DocumentApprovalHistory.svelte`
- Purpose: Structured approval decision history.
- Props: `approvals`.

8. `DocumentExpiryTracker.svelte`
- Purpose: Expiry trigger visibility and alert/escalation checkpoint visibility.
- Props: `expiry`.

9. `DocumentAuditTrail.svelte`
- Purpose: Unified chronological audit stream (versions, approvals, workflow, comments).
- Props: `events`.

## Integration Matrix

- `documents/+page.svelte`
  - Uses: `DocumentKpiCard`, `DocumentRecordsTable`, `DocumentStatusBadge`
- `documents/[id]/+page.svelte`
  - Uses: `DocumentMetadataPanel`, `DocumentVersionTimeline`, `DocumentApprovalHistory`, `DocumentLinkedEntities`, `DocumentExpiryTracker`, `DocumentAuditTrail`
- `projects/[id]/+page.svelte`
  - Uses: `DocumentRecordsTable` in contextual Documents tab
- `properties/[id]/+page.svelte`
  - Uses: `DocumentRecordsTable` in contextual Documents tab
- `units/[id]/+page.svelte`
  - Uses: `DocumentRecordsTable` in contextual Documents tab
- `procurement/vendors/[id]/+page.svelte`
  - Uses: `DocumentRecordsTable` in contextual Documents tab
