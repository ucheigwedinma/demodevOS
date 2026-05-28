# Compliance Monitoring Service (Phase 6)

Phase 6 adds automated expiry/compliance controls for governance-critical documents.

## Trigger Categories

The `documents_documentexpiry.trigger_category` field now supports:

- `building_permit` (Building Permit expiry)
- `insurance` (Insurance expiry)
- `performance_bond` (Performance Bond expiry)
- `eia_renewal` (EIA renewal)
- `warranty_end` (Warranty end date)

## Automation Rules

The monitor runs expiry checks and sends alerts exactly once per lifecycle checkpoint:

- 90-day warning: sent once when document is within `31..90` days to expiry
- 30-day warning: sent once when document is within `0..30` days to expiry
- Expired alert: sent once after expiry date
- Escalation: sent once for expired documents

Idempotency is enforced using these timestamps on `DocumentExpiry`:

- `alert_90_days_sent_at`
- `alert_30_days_sent_at`
- `expired_alert_sent_at`
- `escalated_at`
- `last_checked_at`

## Alert Delivery

For each event, the service sends:

- In-app notification (`apps.notifications.Notification`)
- Email alert (if recipient has email)

Recipients are resolved from document/project memberships, business-unit memberships, document actors, and superusers. Escalation additionally includes governance/legal executive roles in related organizations.

## Project Compliance Score

Service updates all projects with:

- `compliance_score` (`0.00` to `100.00`)
- `compliance_status` (`compliant`, `warning`, `non_compliant`)
- `compliance_last_evaluated_at`

Scoring penalizes expired documents most heavily, then 30-day and 90-day risks.

## Code References

- Service: `server/apps/documents/compliance_monitoring.py`
- Task: `server/apps/documents/tasks.py`
- Manual run command: `server/apps/documents/management/commands/run_documents_compliance_monitor.py`
