# API Test Skeletons Guide

## What Was Added

API test skeleton files were added across backend apps with case IDs mapped to the catalog:

- `server/apps/accounts/test_api_skeleton.py`
- `server/apps/settings/test_api_skeleton.py`
- `server/apps/workflows/test_api_skeleton.py`
- `server/apps/properties/test_api_skeleton.py`
- `server/apps/projects/test_api_skeleton.py`
- `server/apps/finance/test_api_skeleton.py`
- `server/apps/procurement/tests.py`
- `server/apps/crm/test_api_skeleton.py`
- `server/apps/documents/test_api_skeleton.py`
- `server/apps/partners/test_api_skeleton.py`

Shared helper base:

- `server/apps/accounts/api_test_skeleton_utils.py`

## Pattern

Each test method is currently a TODO placeholder (`skipTest`) and includes:

- Case ID from the test catalog (example: `AUTH-004`)
- Scenario title

This gives runnable structure now, while allowing incremental assertion implementation.

## How to Run

Run all tests:

```bash
cd server
.venv/bin/python manage.py test
```

Run only skeleton suites:

```bash
cd server
.venv/bin/python manage.py test \
  apps.accounts.test_api_skeleton \
  apps.settings.test_api_skeleton \
  apps.workflows.test_api_skeleton \
  apps.properties.test_api_skeleton \
  apps.projects.test_api_skeleton \
  apps.finance.test_api_skeleton \
  apps.procurement.tests \
  apps.crm.test_api_skeleton \
  apps.documents.test_api_skeleton \
  apps.partners.test_api_skeleton
```

## Converting a Skeleton to a Real Test

1. Locate the case ID in the method name/docstring.
2. Replace `self.todo_case(...)` with API call + assertions.
3. Keep the case ID in the method name for traceability to catalog and UAT evidence.

