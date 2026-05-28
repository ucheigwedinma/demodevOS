# developerOS — Public Demo

> The operating system for real estate developers in Africa.

**Live product → [developeros.pro](https://developeros.pro)**

---

## What this is

developerOS is a multi-module enterprise SaaS platform built for real estate
developers. It replaces disconnected spreadsheets, WhatsApp groups, and
siloed tools with a single cloud workspace.

This repository is a **public demo** of the codebase architecture.
Proprietary business logic has been replaced with stubs.
The full product is live and serving paying customers.

---

## Modules

| Module | Description |
|---|---|
| Projects | Construction milestones, schedules, risk registers, site reports |
| Finance | General ledger, budgets, payment runs, investor waterfall |
| CRM | Sales pipeline, contact management, lead tracking |
| Procurement | Purchase orders, RFQs, vendor management, 3-way matching |
| Inventory | BOQ planning, material requisitions, warehouse management |
| Properties | Portfolio tracking, unit inventory, valuations, maintenance |
| HR | Recruitment, payroll, leave, org chart, position budgeting |
| Tenants | Lease management, rent tracking, tenant portal |
| Facility Management | Service requests, space occupancy, compliance |
| Workflows | Approval engine, process authority, escalation matrix |
| Support Desk | Ticketing, SLA management, knowledge base |
| Notifications | Real-time WebSocket alerts, email digests |
| Settings | RBAC, feature flags, subscription tiers, org bootstrap |

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Framework | Django 5 + Django REST Framework |
| Auth | JWT (SimpleJWT) + WebAuthn/Passkeys + OAuth (Google, Microsoft) |
| Database | PostgreSQL with full-text and trigram search |
| Cache / Queue | Redis + Celery + Celery Beat |
| WebSockets | Django Channels |
| Background Tasks | Celery with Beat scheduler |
| Storage | Backblaze B2 (media + backups + WAL archiving) |
| API Docs | drf-spectacular (OpenAPI 3) |
| Admin | Django Unfold |
| Security | CSP, HSTS, Permissions Policy, Argon2 hashing, rate limiting |
| Deployment | Docker, Gunicorn, ASGI (Daphne), Nginx Proxy Manager |
| CI/CD | Microsoft Azure DevOps |

---

## Architecture highlights

- **Multi-tenant** — organisation-scoped data isolation across all modules
- **RBAC** — role-based access with contextual access policies per org
- **Workflow engine** — configurable approval chains with escalation rules
- **Feature flags** — per-org module activation and subscription gating
- **Audit logging** — full audit trail via django-auditlog across all models
- **Backup strategy** — daily full backup + 15-min WAL archiving to B2

---

## Running locally

```bash
cp server/.env.example server/.env
docker compose up --build
```

Migrations and seed data run automatically on first boot.

---

## Note on this demo repo

Business logic in the following areas has been replaced with stubs
to protect proprietary algorithms:

- Finance calculation engines (GL, budget, waterfall, payroll)
- Workflow execution engine
- RBAC and contextual access defaults
- BOQ planning engine
- Blueprint and template instantiation
- Quota and module gating logic

The structure, schema, API surface, and architecture are intact and
representative of the full production codebase.

---

## License

MIT — see [LICENSE](./LICENSE)

Built by [Uche Igwedinma](https://github.com/ucheigwedinma)
