Land Acquisition
      ↓
Project Planning
      ↓
Design & Approvals
      ↓
Procurement & Contractor Mobilization
      ↓
Construction Execution
      ↓
Inventory Creation (Units)
      ↓
Sales / Leasing
      ↓
Property Management
      ↓
Revenue Collection
      ↓
Facilities Maintenance
      ↓
Portfolio Performance


Construction Module (DeveloperOS)

Purpose

The Construction Module manages everything that happens on site from groundbreaking to handover.

It controls:
	•	Site mobilization
	•	Contractor execution
	•	Material consumption
	•	Workforce management
	•	Cost tracking
	•	Quality assurance
	•	Safety compliance
	•	Progress verification
	•	Change orders
	•	Site reporting
	•	Defect resolution

It is the operational engine of project delivery.

1. Site Overview Dashboard

This is the construction command center.

Displays:
	•	Project progress %
	•	Schedule variance
	•	Cost variance
	•	Open RFIs
	•	Pending inspections
	•	Safety incidents
	•	Material shortages
	•	Workforce count
	•	Equipment utilization
	•	Quality issues
	•	Delayed tasks
	•	Contractor performance


Visual widgets

Progress Curve
Cost vs Budget
Labour Distribution
Material Consumption
Safety Index
Inspection Status




dev fill keeps bringing the same milestone and phase upon adding more entries 

but you stipulated that entries have been added for



The automated backup system is fully implemented. Here's a summary of what was done:

Docker Compose changes (docker-compose.hostinger.yml):

db — Custom PG config mount (custom-postgresql.conf), wal_archive shared volume, command override to load the config
celery — wal_archive volume (for WAL upload task), ./secrets:/app/secrets:ro (for config backup task), 4 B2 secrets
celery-beat — 4 B2 secrets (reads settings at scheduler init)
volumes — Added wal_archive:
secrets — Added b2_key_id, b2_app_key, b2_bucket_name, b2_endpoint
Before deploying, you'll need to:

Create the B2 secret files on the server:


echo -n 0035787aac6d7710000000001 > ./secrets/b2_key_id
echo -n K003NQpXTlNfP50DUqM5GkPizk/k+IA > ./secrets/b2_app_key
echo -n devOS-backup > ./secrets/b2_bucket_name
echo -n https://s3.eu-central-003.backblazeb2.com > ./secrets/b2_endpoint
Ensure the Celery Docker image includes postgresql-client (for pg_dump/psql):


RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*
Run migrations after deploy: python manage.py migrate — creates BackupLog table + seeds 5 Beat periodic tasks

Verify with: python manage.py restore_backup --list

Yes. Safari caches more aggressively than Chrome, and clearing "Website Data" from the UI doesn't always clear everything (HSTS cache, service worker internals).

Try these in order:

1. Safari → Develop menu → Empty Caches
(If you don't see the Develop menu: Safari → Settings → Advanced → check "Show features for web developers")

2. Also clear Safari's HSTS cache — close Safari completely, then run:


rm ~/Library/Cookies/HSTS.plist
3. Reopen Safari and try https://app.developeros.pro/signup

If that still doesn't work, the nuclear option:

Safari → Settings → Privacy → Manage Website Data → search for developeros → Remove → then restart Safari
This should clear all of Safari's deep caches for the domain. Once it loads fresh, it won't happen again since the server is now returning proper 200s and 301 redirects.