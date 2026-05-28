# QA Runbook

This runbook operationalizes the strategy in [qa-testing-plan-2026.md](/Users/sierra/develop/developerOS/qa-testing-plan-2026.md).

It covers three things:

1. Exact commands for CI, local verification, and staging
2. A Playwright test matrix for the first 15 critical journeys
3. A release checklist for staging signoff and production deployment

## Ground Rules

- Use real seeded data for workflow validation.
- Run fast checks first, then domain tests, then smoke flows.
- Treat Celery, Celery Beat, Redis, storage, and seeds as part of the product.
- For this app, a release is not valid if only frontend or only backend tests passed.

## 1. CI And Environment Commands

## A. Local Pre-PR Validation

### Frontend

```bash
cd /Users/sierra/develop/developerOS/client
npm run check
npm run build
```

### Backend

```bash
cd /Users/sierra/develop/developerOS/server
python -m ruff check .
./.venv/bin/python manage.py check
```

### Fast Critical Backend Tests

```bash
cd /Users/sierra/develop/developerOS/server
./.venv/bin/python manage.py test apps.settings.tests_seed_suites --keepdb --noinput
./.venv/bin/python manage.py test apps.procurement.tests --keepdb --noinput
./.venv/bin/python manage.py test apps.tenants.tests_registry apps.tenants.tests_operations --keepdb --noinput
./.venv/bin/python manage.py test apps.facility_management.tests_service_requests apps.facility_management.tests_space_occupancy --keepdb --noinput
./.venv/bin/python manage.py test apps.finance.tests_cost_tracking_hooks apps.finance.tests_journal_numbers --keepdb --noinput
./.venv/bin/python manage.py test apps.projects.tests apps.projects.tests_role_library apps.projects.tests_team_dissolution --keepdb --noinput
```

### Focused Domain Commands By Change Area

#### Procurement changes

```bash
cd /Users/sierra/develop/developerOS/server
./.venv/bin/python manage.py test apps.procurement.tests --keepdb --noinput
```

#### Tenants and lease automation changes

```bash
cd /Users/sierra/develop/developerOS/server
./.venv/bin/python manage.py test apps.tenants.tests_registry apps.tenants.tests_operations apps.tenants.tests_dashboard --keepdb --noinput
```

#### Facility Management changes

```bash
cd /Users/sierra/develop/developerOS/server
./.venv/bin/python manage.py test \
  apps.facility_management.tests_registry \
  apps.facility_management.tests_space_occupancy \
  apps.facility_management.tests_service_requests \
  apps.facility_management.tests_maintenance \
  apps.facility_management.tests_health_safety \
  apps.facility_management.tests_utilities \
  --keepdb --noinput
```

#### CRM changes

```bash
cd /Users/sierra/develop/developerOS/server
./.venv/bin/python manage.py test \
  apps.crm.tests_activity_task_management \
  apps.crm.tests_analytics_reporting \
  apps.crm.tests_campaign_automations \
  apps.crm.tests_kyc_stage_gating \
  apps.crm.tests_opportunity_deal_automations \
  apps.crm.tests_property_matching_engine \
  --keepdb --noinput
```

#### HR changes

```bash
cd /Users/sierra/develop/developerOS/server
./.venv/bin/python manage.py test \
  apps.hr.tests_org_chart \
  apps.hr.tests_position_automation \
  apps.hr.tests_position_budgeting \
  apps.hr.tests_positions_roles \
  apps.hr.tests_staff_mapping \
  apps.hr.tests_teams \
  --keepdb --noinput
```

## B. Recommended CI Pipeline Order

### Stage 1. Static Validation

```bash
cd /Users/sierra/develop/developerOS/client
npm run check
npm run build

cd /Users/sierra/develop/developerOS/server
python -m ruff check .
./.venv/bin/python manage.py check
```

### Stage 2. Seed And Platform Safety

```bash
cd /Users/sierra/develop/developerOS/server
./.venv/bin/python manage.py test apps.settings.tests_seed_suites --keepdb --noinput
```

### Stage 3. Workflow-Critical Regression Pack

```bash
cd /Users/sierra/develop/developerOS/server
./.venv/bin/python manage.py test \
  apps.procurement.tests \
  apps.tenants.tests_registry \
  apps.tenants.tests_operations \
  apps.facility_management.tests_service_requests \
  apps.facility_management.tests_space_occupancy \
  apps.finance.tests_cost_tracking_hooks \
  apps.finance.tests_journal_numbers \
  --keepdb --noinput
```

### Stage 4. Full Domain Pack For Nightly Or Release Candidate

```bash
cd /Users/sierra/develop/developerOS/server
./.venv/bin/python manage.py test \
  apps.analytics.tests \
  apps.crm.tests_activity_task_management \
  apps.crm.tests_analytics_reporting \
  apps.crm.tests_campaign_automations \
  apps.crm.tests_kyc_stage_gating \
  apps.crm.tests_opportunity_deal_automations \
  apps.crm.tests_property_matching_engine \
  apps.facility_management.tests_assets \
  apps.facility_management.tests_dashboard \
  apps.facility_management.tests_documents \
  apps.facility_management.tests_health_safety \
  apps.facility_management.tests_maintenance \
  apps.facility_management.tests_registry \
  apps.facility_management.tests_service_requests \
  apps.facility_management.tests_space_occupancy \
  apps.facility_management.tests_utilities \
  apps.finance.tests_cost_tracking_hooks \
  apps.finance.tests_journal_numbers \
  apps.hr.tests_org_chart \
  apps.hr.tests_position_automation \
  apps.hr.tests_position_budgeting \
  apps.hr.tests_positions_roles \
  apps.hr.tests_staff_mapping \
  apps.hr.tests_teams \
  apps.partners.tests_document_kyc_automations \
  apps.procurement.tests \
  apps.projects.tests \
  apps.projects.tests_role_library \
  apps.projects.tests_team_dissolution \
  apps.settings.tests_division_operational_metadata \
  apps.settings.tests_seed_suites \
  apps.support_desk.tests_customer_ticketing_automations \
  apps.tenants.tests_dashboard \
  apps.tenants.tests_operations \
  apps.tenants.tests_registry \
  apps.tenants.tests_urls \
  --keepdb --noinput
```

## C. Staging Environment Bring-Up

### Start Core Services

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.staging.yml up -d db redis server celery celery-beat client console
```

### Run Migrations

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.staging.yml exec server python manage.py migrate
```

### Backend Health Checks

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.staging.yml exec server python manage.py check
docker compose -f docker-compose.staging.yml exec server python manage.py check --deploy --settings=config.settings.production
```

Note:
- If staging has its own settings module, replace `config.settings.production` with the actual staging settings module.

### Celery And Scheduler Health

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.staging.yml exec celery celery -A config inspect ping
docker compose -f docker-compose.staging.yml exec server python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(PeriodicTask.objects.count())"
```

### Seed Platform Data In Staging

#### Platform-wide baseline

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.staging.yml exec server python manage.py seed_platform_suite --include-ops --include-workflows
```

#### Demo/UAT environment

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.staging.yml exec server python manage.py seed_demo_suite --flush --include-workflows
```

### Backup And Restore Smoke

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.staging.yml exec server python manage.py restore_backup --list
```

### Staging Regression Pack

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.staging.yml exec server python manage.py test \
  apps.procurement.tests \
  apps.tenants.tests_registry \
  apps.tenants.tests_operations \
  apps.facility_management.tests_service_requests \
  apps.facility_management.tests_space_occupancy \
  apps.finance.tests_cost_tracking_hooks \
  apps.settings.tests_seed_suites \
  --keepdb --noinput
```

## D. Production-Safe Verification Commands

These are intended to be non-destructive.

### Service Status

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.hostinger.yml ps
docker compose -f docker-compose.hostinger.yml logs --tail=100 server
docker compose -f docker-compose.hostinger.yml logs --tail=100 celery
docker compose -f docker-compose.hostinger.yml logs --tail=100 celery-beat
```

### Django Health

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.hostinger.yml exec server python manage.py check
docker compose -f docker-compose.hostinger.yml exec server python manage.py check --deploy --settings=config.settings.production
```

### Scheduler And Backup Health

```bash
cd /Users/sierra/develop/developerOS
docker compose -f docker-compose.hostinger.yml exec celery celery -A config inspect ping
docker compose -f docker-compose.hostinger.yml exec server python manage.py restore_backup --list
```

## 2. Playwright Test Matrix

This repo does not currently include Playwright. This matrix is the recommended first automation pack once Playwright is added.

Suggested folder structure:

```text
tests/e2e/
  auth/
  crm/
  procurement/
  tenants/
  facility/
  finance/
  documents/
```

Suggested tags:

- `@smoke`
- `@critical`
- `@workflow`
- `@finance`
- `@mobile`
- `@a11y`

## Top 15 Critical Journeys

| ID | Area | Priority | Preconditions | Core Steps | Assertions |
|---|---|---|---|---|---|
| PW-01 | Authentication | P0 | Valid admin user | Login, open dashboard, logout | Session created, dashboard loads, logout redirects cleanly |
| PW-02 | IAM / Access | P0 | Admin and restricted user | Login as restricted user, open protected routes, attempt create/edit | Unauthorized actions blocked, allowed routes still work |
| PW-03 | CRM Lead Funnel | P1 | Seeded CRM org | Create lead, advance stage, attach contact details | Lead persists, stage updates, activity history visible |
| PW-04 | CRM To Reservation | P1 | Lead exists | Convert lead to reservation/customer path | Downstream linked records created without broken references |
| PW-05 | Project Creation | P0 | Seeded templates | Create project from template | Project saves, phases/tasks load, project dashboard reflects new project |
| PW-06 | Project Planning | P1 | Template and planning data | Open planning pages, select template, edit tasks/activities | Drawers work, save succeeds, table/detail refreshes correctly |
| PW-07 | Procurement Requisition | P0 | Vendor and org seeded | Create requisition | Requisition appears in list, status and totals correct |
| PW-08 | Procurement RFQ | P0 | Requisition exists | Create RFQ from requisition, add quotes | RFQ appears, quote count updates, selected vendor fields remain consistent |
| PW-09 | Vendor Selection | P0 | RFQ with quotes | Compare vendors, select winning vendor | Winner persists, RFQ detail reflects selected vendor, scoring visible |
| PW-10 | Purchase Order + GRN | P0 | Selected vendor and approved requisition | Issue PO, create GRN | PO status updates, GRN created, linked vendor surfaces correctly |
| PW-11 | Tenant Registry + Lease Context | P0 | Seeded property/facility/space | Create tenant from registry | Tenant saved, lease context exists, registry list refreshes |
| PW-12 | Billing Cycle | P0 | Tenant with active lease and charge rules | Trigger billing workflow or wait seeded due cycle | Invoice created, tenant balance changes, notice visible |
| PW-13 | Payment + Receipt | P0 | Sent invoice exists | Record payment | Invoice status updates, receipt generated, ledger evidence present |
| PW-14 | Tenant Service Request | P0 | Tenant exists | Log issue, route to facility, complete resolution | Work order created, SLA set, status transitions visible |
| PW-15 | Document Workflow | P1 | Seeded org and linked records | Upload document, link to context, move status | Document visible in repository and context-specific views |

## Recommended Playwright Specs

### Smoke Pack

- `auth/login.spec.ts`
- `auth/role-access.spec.ts`
- `procurement/vendor-to-po.spec.ts`
- `tenants/tenant-billing-payment.spec.ts`
- `facility/service-request-resolution.spec.ts`

### Broader Workflow Pack

- `crm/lead-to-reservation.spec.ts`
- `projects/template-project-creation.spec.ts`
- `project-planning/planning-edit-drawers.spec.ts`
- `procurement/rfq-vendor-selection.spec.ts`
- `documents/document-linkage.spec.ts`

## Playwright Execution Commands

Once Playwright is added:

### Install

```bash
cd /Users/sierra/develop/developerOS/client
npm install -D @playwright/test
npx playwright install
```

### Run smoke

```bash
cd /Users/sierra/develop/developerOS/client
npx playwright test --grep @smoke
```

### Run critical workflow pack

```bash
cd /Users/sierra/develop/developerOS/client
npx playwright test --grep @critical
```

### Run mobile viewport pack

```bash
cd /Users/sierra/develop/developerOS/client
npx playwright test --project="Mobile Chrome"
```

## 3. Release Checklist

## A. Pre-Release Preparation

- Confirm release scope and changed modules.
- Identify which workflows are touched.
- Map changed modules to backend test packs.
- Confirm migrations included in release are reviewed.
- Confirm seed changes, workflow changes, and periodic-task changes are reviewed.
- Confirm rollback plan exists.
- Confirm backup status before deployment.

## B. PR And CI Gate

- `npm run check` passes.
- `npm run build` passes.
- `ruff` passes.
- `python manage.py check` passes.
- Changed-domain tests pass.
- Seed suite registry tests pass.
- No unresolved Severity 1 defect remains.

## C. Staging Release Candidate Gate

- Deploy release candidate to staging.
- Run `python manage.py migrate`.
- Run `python manage.py check`.
- Run `python manage.py check --deploy --settings=config.settings.production` or staging equivalent.
- Verify `celery` worker responds to `inspect ping`.
- Verify periodic tasks exist.
- Seed staging with the correct suite.
- Run staging regression pack.
- Execute the manual or Playwright smoke pack.
- Confirm top workflows in changed modules.

## D. Manual Staging UAT Checklist

### Core platform

- Login works for admin.
- Login works for limited role.
- Navigation menu renders correctly.
- Drawers open, close, and scroll properly.
- Toasts and saves complete cleanly.

### Procurement

- Vendors list loads.
- Vendor drawer view/edit/delete works.
- Requisition creation works.
- RFQ flow works.
- Vendor selection works.
- PO and GRN linkage works.

### Tenants

- Tenant registry loads.
- Add tenant works.
- Lease context exists.
- Billing and payments reflect changes.
- Service request path remains intact.

### Facility Management

- Registry and space occupancy load.
- Service requests create and route correctly.
- Maintenance lists load and paginate.
- Utilities and health/safety pages render and save.

### Finance

- Invoice list loads.
- Payment recording works.
- Receipt generation works.
- Journals and ledger surfaces remain available.

### Documents

- Repository loads.
- Linked document panels load.
- Upload or document generation path works if touched.

## E. Production Deployment Checklist

- Backup verified before deploy.
- Maintenance window or release window confirmed.
- Production secrets unchanged or validated.
- Deploy performed with reviewed compose file.
- Migrations run successfully.
- Static assets and client build published successfully.
- Worker and beat services restarted if required.

## F. Post-Deploy Smoke Checklist

Run only non-destructive checks.

- Production containers are healthy.
- Django `check` passes.
- Celery ping passes.
- Home/dashboard loads.
- Admin can log in.
- One representative page per changed module loads.
- One representative list page loads.
- One representative drawer opens.
- No major console or server errors in logs.
- Backup listing command works.

## G. Rollback Decision Criteria

Rollback immediately if any of the following occurs:

- authentication broken
- cross-org data exposure
- migrations fail or partially corrupt key workflows
- finance posting or billing integrity issue
- Celery worker or beat cannot recover
- critical tenant, procurement, or service-request workflows are blocked

## H. Evidence Required For Signoff

Capture and store:

- CI results
- exact commit or release tag
- test run output
- staging smoke evidence
- screenshots or video for critical manual checks
- migration output
- post-deploy smoke output
- open defect list with severity and disposition

## Recommended Immediate Adoption Order

1. Use the CI and staging command sections in this file as the team’s shared QA baseline.
2. Add Playwright and automate the first five smoke journeys.
3. Expand the smoke pack into the full 15-journey matrix.
4. Make the release checklist mandatory before every production deployment.

## Related Docs

- [qa-testing-plan-2026.md](/Users/sierra/develop/developerOS/qa-testing-plan-2026.md)
- [prod-seeds.md](/Users/sierra/develop/developerOS/prod-seeds.md)
