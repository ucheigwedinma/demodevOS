# QA Testing Plan 2026

## Purpose

This plan defines how a 2026 QA team should test `developerOS` end to end across web, mobile shells, background jobs, seeded environments, and cross-module workflows.

The goal is not just to find bugs. The goal is to make releases predictable, safe, auditable, and fast across a very broad enterprise product surface.

## App Context

`developerOS` is not a single workflow app. It is a multi-domain operating platform with interconnected modules, including:

- CRM
- Projects
- Project Planning
- Procurement
- Construction
- Properties
- Tenants
- Facility Management
- Finance
- Documents
- HR
- IAM
- Partners
- Reports
- Support Desk
- Settings and seed suites

## Current Repo Reality

Based on the current repository:

- Frontend stack: `SvelteKit 2`, `Svelte 5`, `Tailwind 4`, `Capacitor` for iOS and Android shells.
- Frontend validation in repo today: `npm run check` using `svelte-check`.
- Backend stack: `Django 5.2`, `Django REST Framework`, `django-filter`, `Celery`, `django-celery-beat`, `Redis`, `PostgreSQL`, `django-guardian`, audit logging, document tooling, OCR, and reporting support.
- Backend automated tests already exist across key domains such as CRM, Facility Management, Finance, HR, Procurement, Projects, Settings, Support Desk, and Tenants.
- Seed and operational bootstrap commands already exist and should be part of QA environment preparation.
- Backup and scheduled-job behavior matter because the product depends on Celery, Beat, storage, and seeded operational workflows.

## What A 2026 QA Expert Would Assume

A QA lead in 2026 would treat this app as:

- a workflow platform, not just a CRUD app
- a role-sensitive enterprise system
- a background-automation-heavy product
- a mobile-plus-web surface
- a data-integrity-sensitive system where cross-module regression risk is high

That means the testing strategy must be layered.

## Quality Strategy

The test model should follow this order:

1. Fast feedback on every commit
2. Stable API and workflow integration coverage
3. Real browser end-to-end coverage for critical journeys
4. Scheduled exploratory and risk-based manual testing
5. Non-functional validation before every major release
6. Production smoke checks after deployment

## Primary Quality Risks

The highest-risk areas for this app are:

- Cross-module workflows that mutate shared records
- Role-based access and visibility differences
- Seeded demo data drifting from actual production assumptions
- Celery and scheduled task side effects
- Financial posting and irreversible operations
- Lease, occupancy, procurement, and support automations
- Large record sets and dashboard responsiveness
- Mobile shell regressions after frontend changes
- Backup, restore, and disaster-recovery assumptions
- Environment-specific issues between local, staging, and production

## Test Environments

### 1. Developer Environment

Purpose:

- fast local feedback
- component debugging
- targeted regression reproduction

Used for:

- `svelte-check`
- targeted Django tests
- developer smoke checks

### 2. CI Validation Environment

Purpose:

- enforce merge gates
- block obvious regressions early

Should run:

- frontend static checks
- backend linting
- targeted backend test suites by changed module
- smoke API contract checks

### 3. Shared Integration Environment

Purpose:

- validate services working together
- test seeded data and scheduled jobs

Must include:

- PostgreSQL
- Redis
- Celery worker
- Celery Beat
- object storage equivalent or test bucket
- representative org data

### 4. Staging / Pre-Production

Purpose:

- release candidate validation
- UAT
- performance and rollback rehearsal

Must mirror production as closely as possible in:

- infrastructure topology
- secrets model
- background jobs
- storage integrations
- seed setup
- build mode

### 5. Production Smoke Layer

Purpose:

- post-deploy confidence without destructive testing

Used for:

- authenticated smoke flows
- read-only dashboard validation
- job heartbeat checks
- health and backup verification

## Test Data Strategy

QA should use three test-data profiles:

### Minimal Smoke Dataset

Used for:

- CI
- fast validation
- narrow regressions

Includes:

- 1 org
- 1 admin
- a few properties, units, tenants, vendors, projects, and invoices

### Operational Dataset

Used for:

- integration testing
- workflow validation
- queue behavior

Includes:

- realistic linked records across CRM, Properties, Procurement, Finance, Tenants, and Facility Management

### High-Volume Dataset

Used for:

- performance
- virtualization
- pagination
- search
- reporting

Includes:

- hundreds or thousands of records across key list-heavy modules

## Seed Execution For QA

Leverage the existing suite commands instead of ad hoc seeding:

- `./.venv/bin/python manage.py seed_demo_suite --flush --include-workflows`
- `./.venv/bin/python manage.py seed_platform_suite --include-ops --include-workflows`

QA should maintain:

- one smoke-ready seed profile
- one full operational regression seed profile
- one performance seed profile

## Recommended Test Tooling For 2026

### Existing Tooling To Keep

- `npm run check`
- Django test runner
- module-specific backend tests
- seed suites

### Tooling To Add

- `Playwright` for browser end-to-end and role-based journeys
- `Vitest` plus Svelte Testing Library for frontend component and logic tests
- API schema and contract verification in CI
- load testing with `k6` or `Locust`
- accessibility automation using `axe-core`
- visual regression for high-value dashboards and drawer workflows

## Test Layers

## 1. Static and Build Validation

Run on every PR:

- Svelte type and template validation
- TypeScript validation
- Python linting with `ruff`
- dependency vulnerability scanning
- production build verification for client
- Django startup and import sanity

Commands:

```bash
cd client
npm run check
npm run build

cd /Users/sierra/develop/developerOS/server
python -m ruff check .
python manage.py check
```

## 2. Backend Unit and Domain Tests

Scope:

- serializers
- validators
- model invariants
- workflow helpers
- permission rules
- finance calculations
- tenant and procurement automations

How:

- add narrow tests for every defect fixed
- keep tests close to the domain module
- isolate side effects where possible

Priority domains:

- Tenants
- Facility Management
- Procurement
- Finance
- CRM
- Projects
- Settings and seed orchestration

## 3. API Integration Tests

Scope:

- authenticated API flows
- list filtering
- pagination
- create/update/delete behavior
- error handling
- cross-entity linkage

Examples:

- create vendor -> appears in procurement lists -> editable -> deletable if not referenced
- create tenant -> lease context exists -> related modules update correctly
- create service request -> work order created -> SLA fields set
- receive payment -> invoice state updates -> ledger entries created

How:

- use Django API tests with realistic linked fixtures
- assert both response correctness and persisted side effects

## 4. Workflow and Event Automation Tests

This is mandatory for this app.

Scope:

- Celery-triggered jobs
- scheduled syncs
- event-driven automations
- retries and idempotency

Critical automation suites:

- lease created
- lease expiry approaching
- lease terminated
- billing cycle date
- payment received
- payment overdue
- tenant logs issue
- issue resolved
- move-in
- move-out
- backup and restore schedules

How:

- test each trigger independently
- test repeat execution to verify idempotency
- test failure handling and retry safety
- verify downstream state in all touched modules

## 5. Frontend Component and Interaction Tests

Add this layer if not already present.

Scope:

- tables
- drawers
- forms
- filters
- search
- pagination
- inline status badges
- toasts
- route guards

High-priority UI patterns to test:

- drawers replacing inline detail views
- forms that switch between create/edit modes
- list refresh after mutations
- optimistic and non-optimistic save flows
- long forms and scroll behavior
- empty, loading, and error states

## 6. End-to-End Browser Tests

This is where a QA expert would spend the most design effort.

### Critical E2E Journeys

#### Authentication and Access

- login
- logout
- expired session handling
- role-based page visibility
- restricted action blocking

#### CRM to Customer Lifecycle

- create lead
- advance lead
- convert to customer or reservation
- handoff into downstream workflow

#### Project Delivery Lifecycle

- create project
- apply template
- manage phases/tasks
- update progress
- verify dashboards and reports

#### Procurement Flow

- create requisition
- create RFQ
- compare/select vendor
- issue PO
- create GRN
- verify downstream records

#### Tenant Lifecycle

- create tenant with lease context
- validate lease drawer and registry
- billing cycle generation
- payment and receipt
- service request creation
- move-out closure

#### Facility Flow

- register facility and space
- allocate tenant or booking
- log maintenance request
- complete work order
- verify SLA and tenant feedback loop

#### Finance Flow

- create bill or invoice
- receive payment
- verify ledger impact
- verify aging or status changes

#### Documents Flow

- upload document
- status workflow
- repository visibility
- linked context retrieval

## 7. Exploratory Testing

A strong QA team in 2026 still does structured exploratory testing.

Use charters such as:

- break role boundaries
- break cross-module assumptions
- break date and timezone logic
- break seeded demo assumptions
- break long-form edit and drawer flows
- break search, pagination, and filters after mutations
- break file upload and document linkage
- break workflows when records are partially configured

Exploratory sessions should be scheduled weekly for high-change areas.

## 8. Accessibility Testing

Required for enterprise quality.

Test:

- keyboard-only navigation
- focus trap in drawers and modals
- form label association
- screen-reader landmarks
- contrast
- icon-only buttons with proper labels
- table semantics
- reduced-motion behavior where applicable

How:

- automated `axe` scans on key routes
- manual keyboard walkthroughs
- manual screen-reader spot checks on high-value workflows

## 9. Performance Testing

This app has many dense dashboards and large data tables, so performance testing must be intentional.

Test:

- list rendering with hundreds and thousands of records
- dashboard load time
- search/filter latency
- report generation time
- background job throughput
- drawer open/edit/save responsiveness
- mobile web bundle performance

Suggested targets:

- primary page interactive under 3 seconds on staging baseline
- table filter response under 1 second on common datasets
- drawer open under 300ms perceived latency after data load

## 10. Security Testing

Scope:

- authentication and session handling
- authorization bypass
- tenant/org data isolation
- direct object reference checks
- CSRF and cookie configuration
- upload validation
- secret handling
- injection testing on filters and search
- audit logging presence for sensitive actions

Release gates should include:

- `python manage.py check --deploy`
- permission regression tests
- basic authenticated and unauthenticated route scanning

## 11. Mobile and PWA Testing

Because Capacitor is installed, QA should not treat the app as browser-only.

Test:

- iOS shell
- Android shell
- keyboard behavior in forms
- deep links if supported
- offline or interrupted connectivity behavior
- orientation changes
- status bar and safe area layout
- file upload and download behavior on mobile

## 12. Backup, Restore, and Resilience Testing

This is a real production requirement for this platform.

Test:

- scheduled backup jobs run
- backup artifacts are created
- restore listing works
- restore rehearsal succeeds in non-production
- WAL/archive expectations hold
- worker restart recovery
- Beat restart recovery

How:

- monthly restore drill in staging
- post-release verification of backup heartbeat
- explicit disaster-recovery checklist

## Module Test Matrix

| Module | Functional | Integration | E2E | Performance | Security | Accessibility |
|---|---|---|---|---|---|---|
| CRM | High | High | High | Medium | High | Medium |
| Projects | High | High | High | High | Medium | Medium |
| Project Planning | High | Medium | High | High | Medium | High |
| Procurement | High | High | High | Medium | High | High |
| Tenants | High | Very High | High | Medium | High | High |
| Facility Management | High | Very High | High | High | Medium | High |
| Finance | Very High | Very High | High | Medium | Very High | Medium |
| Documents | High | High | Medium | Medium | High | High |
| HR | High | Medium | Medium | Medium | Very High | Medium |
| IAM | Very High | High | High | Low | Very High | Medium |
| Reports | Medium | Medium | Medium | Very High | Medium | Medium |
| Settings / Seeds | High | High | Medium | Low | High | Low |

## Release Gates

## Pull Request Gate

Required:

- frontend check passes
- backend lint passes
- changed-module tests pass
- no critical security or permission regression

## Release Candidate Gate

Required:

- full critical backend suites pass
- full browser smoke pack passes
- manual QA signoff on changed domains
- Celery and scheduled workflows validated in staging
- seed and migration rehearsal complete

## Production Gate

Required:

- migration plan reviewed
- rollback plan reviewed
- backup health verified before deploy
- post-deploy smoke pack executed

## Suggested Test Suites By Cadence

### On Every Commit

- lint
- static checks
- changed-module tests

### On Every PR

- API smoke pack
- critical UI smoke pack
- permission smoke pack

### Nightly

- broader integration suite
- workflow suite
- seeded regression suite

### Weekly

- exploratory testing
- accessibility sweep on changed areas
- mobile smoke pack

### Pre-Release

- full critical-path E2E
- performance regression
- security review
- backup and restore verification

## Defect Classification

### Severity 1

- financial corruption
- cross-org data leak
- broken auth
- broken payment or lease workflow
- production data loss risk

### Severity 2

- blocked business-critical module
- automation failure with visible operational impact
- broken create/edit/delete in key workflows

### Severity 3

- non-blocking workflow errors
- reporting inaccuracies without data corruption
- mobile layout breakage on secondary routes

### Severity 4

- cosmetic issues
- copy issues
- low-impact UX friction

## QA Exit Criteria For A Release

A release should not be signed off unless:

- no Severity 1 defects remain open
- no unresolved cross-module data integrity risk remains
- all changed critical workflows are covered by automated or executed manual tests
- post-migration staging validation is complete
- rollback and restore paths are known

## Recommended Immediate Next Steps

### Phase 1: Strengthen What Already Exists

- formalize module-level Django test ownership
- enforce `npm run check` and Django test gates in CI
- create a stable smoke seed profile using the seed suite commands

### Phase 2: Close Major Gaps

- add Playwright
- add Vitest plus Svelte Testing Library
- add accessibility automation
- add a workflow regression suite for Celery-driven automations

### Phase 3: Mature Release Quality

- add performance baselines
- add mobile smoke automation
- add restore-drill runbooks
- add production smoke dashboards and release scorecards

## Suggested First Automation Pack

If QA can automate only 15 journeys first, these should be the first 15:

1. Login and logout
2. Role-based page access
3. Create project from template
4. Create requisition
5. Create RFQ
6. Select winning vendor
7. Create purchase order
8. Create goods receipt
9. Create tenant with lease context
10. Edit tenant profile
11. Run billing cycle and verify invoice
12. Record payment and verify receipt
13. Log tenant service request
14. Resolve service request and verify feedback path
15. Run backup/restore listing smoke

## Summary

A QA expert in 2026 would test this app using a layered strategy:

- fast static and unit checks
- strong integration and workflow tests
- browser automation for critical journeys
- manual exploratory testing for cross-module risk
- non-functional validation for accessibility, performance, security, and resilience

For `developerOS`, the strongest QA investment is not in isolated CRUD tests. It is in verifying business workflows, permissions, background jobs, seeded environments, and cross-module data integrity.
