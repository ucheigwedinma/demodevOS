# Expiry Cron Scheduler (Phase 6)

Document compliance automation is scheduled via `django-celery-beat`.

## Periodic Task

- Name: `Document Expiry Compliance Monitor`
- Task: `documents.run_expiry_compliance_monitor`
- Schedule: Daily at `06:00 UTC`

## Migration

Seed migration:

- `server/apps/documents/migrations/0013_seed_phase6_expiry_monitor_periodic_task.py`

This migration is idempotent and safe to re-run on new environments.

## Worker Requirements

Run both services in production:

1. Celery worker
2. Celery beat scheduler

Example commands:

```bash
celery -A config worker -l info
celery -A config beat -l info
```

## Manual Execution

For ad-hoc checks:

```bash
python3 manage.py run_documents_compliance_monitor
python3 manage.py run_documents_compliance_monitor --date 2026-03-01
```
