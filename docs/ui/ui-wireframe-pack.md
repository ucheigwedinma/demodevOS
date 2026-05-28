# UI Wireframe Pack (Phase 9)

This wireframe pack maps the implemented information architecture for the Documents module.

## 1) Main Repository Dashboard

Route: `client/src/routes/documents/+page.svelte`

```text
+--------------------------------------------------------------------------------+
| Document Repository                                                            |
| Governance dashboard for approvals, expiries, risk, and compliance posture.   |
+--------------------------------------------------------------------------------+
| Search | Status | Category | Project                                           |
+--------------------------------------------------------------------------------+
| Pending Approval | Exp<=30 | Exp31-60 | Exp61-90 | High-Risk | Recently Mod. |
+--------------------------------------------------------------------------------+
| Documents Pending Approval      | Expiring in 30/60/90 Days                   |
| - number/title/status/context   | - document/trigger/expiry/days              |
+---------------------------------+----------------------------------------------+
| High-Risk Contracts             | Recently Modified                            |
| - filtered records              | - document/version/uploaded                  |
+---------------------------------+----------------------------------------------+
| Compliance Score per Project                                                   |
| - project/status/score/evaluated                                               |
+--------------------------------------------------------------------------------+
| Repository Browser (structured filter output)                                  |
+--------------------------------------------------------------------------------+
```

## 2) Contextual Tabs

### 2.1 Project Page

Route: `client/src/routes/projects/[id]/+page.svelte`

```text
Tabs: Overview | Phases | Milestones | Tasks | Costs | Documents | Timeline

Documents tab:
- Auto-filtered repository table where `project={project_id}`
```

### 2.2 Land Page (Property)

Route: `client/src/routes/properties/[id]/+page.svelte`

```text
Tabs: Overview | Units | Ownership | Images | Documents | Valuations | Encumbrances

Documents tab now includes:
- Repository Documents (auto-filter `land={property_id}`)
- Existing property file attachments upload/listing panel
```

### 2.3 Unit Page

Route: `client/src/routes/units/[id]/+page.svelte`

```text
Tabs: Overview | Documents

Documents tab:
- Auto-filtered repository table where `unit={unit_id}`
```

### 2.4 Vendor Page

Route: `client/src/routes/procurement/vendors/[id]/+page.svelte`

```text
Tabs: Vendor Profile | Purchase Orders | Documents

Documents tab:
- Auto-filtered repository table where `vendor={vendor_id}`
```

## 3) Document Detail Page

Route: `client/src/routes/documents/[id]/+page.svelte`

```text
+--------------------------------------------------------------------------------+
| Breadcrumb + Document Title                                                    |
+--------------------------------------------------------------------------------+
| Metadata Panel                                                                 |
+--------------------------------------------------------------------------------+
| Version Timeline                    | Linked Entities                          |
+-------------------------------------+------------------------------------------+
| Approval History                    | Expiry Tracker                           |
+-------------------------------------+------------------------------------------+
| Audit Trail                                                                    |
+--------------------------------------------------------------------------------+
```

Sections delivered:
- Metadata Panel
- Version Timeline
- Approval History
- Linked Entities
- Audit Trail
- Expiry Tracker
