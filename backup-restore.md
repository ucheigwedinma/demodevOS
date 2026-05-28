# Backup & Restore Runbook

Operational guide for the DeveloperOS backup system. Audience: **Platform
Operators** (the same people with Django `/admin/` access). Customer
Organizations are not involved in this process — backups are platform-wide.

> Previous content of this file was a 2024 Hostinger deploy scratchpad
> (NPM container IPs, network connect commands, **a plaintext database
> password**). It was not a DR runbook. It has been removed; if those
> deploy notes are still needed they are in git history at the commit
> before this one. **The leaked password must be rotated** — see
> `## Security follow-ups` at the end of this file.

## What's backed up

Five Celery tasks live in `apps/backup/tasks.py`:

| Task | Source | Destination | Notes |
|------|--------|-------------|-------|
| `run_full_backup` | `pg_dump` of the live DB | `b2://developeros-backups/database/full/` | Logical (SQL), gzipped |
| `upload_wal_archives` | `/wal_archive/` | `b2://.../database/wal/<YYYYMMDD>/` | PostgreSQL writes WAL via `archive_command`, task uploads & deletes locally |
| `sync_media_backup` | `MEDIA_ROOT` | `b2://.../media/` | Skips files already at the destination with matching size |
| `backup_config` | secrets dir + `.env.prod` | `b2://.../config/<filename>.tar.gz.enc` | Fernet-encrypted with a key derived from `SECRET_KEY` |
| `cleanup_old_backups` | (sweep) | (deletes from B2) | Honours retention settings |

All upload destinations live in a single Backblaze B2 bucket
(`B2_BUCKET_NAME`, default `developeros-backups`).

## Schedule

Defined in `server/config/settings/base.py` under `CELERY_BEAT_SCHEDULE`.
DatabaseScheduler syncs these into `django_celery_beat` on Beat startup;
overrides via `/admin/django_celery_beat/periodictask/` are honoured.

| Beat entry | Cadence | Task |
|------------|---------|------|
| `backup-database-full` | Daily 03:00 UTC | `run_full_backup` |
| `backup-wal-upload` | Every 15 min | `upload_wal_archives` |
| `backup-media-sync` | Daily 04:00 UTC | `sync_media_backup` |
| `backup-config-snapshot` | Daily 04:30 UTC | `backup_config` |
| `backup-cleanup-old` | Sunday 05:00 UTC | `cleanup_old_backups` |

## Retention

Configured in `base.py`:

| Class | Default | Setting |
|-------|---------|---------|
| Full DB | 30 days | `BACKUP_FULL_RETENTION_DAYS` |
| WAL | 7 days | `BACKUP_WAL_RETENTION_DAYS` |
| Config | 30 days | `BACKUP_CONFIG_RETENTION_DAYS` |
| Media | (no automatic deletion) | — |

`cleanup_old_backups` enforces these every Sunday.

## Recovery objectives

> These targets need to be **agreed by the team** and filled in. Until
> they are, treat the values below as starting points, not commitments.

| Metric | Current target | Notes |
|--------|----------------|-------|
| RPO (data-loss tolerance) | _TBD — proposal: 15 min for DB_ | Bounded by WAL upload cadence |
| RTO (time to recover) | _TBD — proposal: 2 hours_ | Dominated by full pg_dump restore time |
| Drill cadence | _TBD — proposal: quarterly_ | See "Drills" below |

## Health monitoring

Every task writes a `BackupLog` row (model: `apps.backup.models.BackupLog`)
with status, file name, B2 path, size, duration, and error message on
failure. Surface these in a regular check:

```sql
-- Most recent run per backup type
SELECT DISTINCT ON (backup_type) backup_type, status, file_name, completed_at, error_message
FROM apps_backup_backuplog
ORDER BY backup_type, started_at DESC;
```

A run is healthy if `status = 'completed'` and `completed_at` is within
the expected window for that type:

| Type | Stale threshold |
|------|-----------------|
| `full` | > 26 h |
| `wal` | > 30 min |
| `media` | > 26 h |
| `config` | > 26 h |

Consider wiring an alert (e.g. via the `notifications` app) when any of
these are exceeded.

## Restore procedures

All restore actions are run via the `restore_backup` management command,
which lives in `apps/backup/management/commands/restore_backup.py` and
is run inside the Django container.

### List what's available

```bash
docker compose -f docker-compose.staging.yml exec server \
  python manage.py restore_backup --list
docker compose ... exec server \
  python manage.py restore_backup --list --type full
```

### Restore the latest full DB backup (most common path)

```bash
docker compose ... exec server \
  python manage.py restore_backup --latest
```

The command downloads the most recent `database/full/*.sql.gz`,
decompresses it, and pipes it into `psql -f`. The command **overwrites
the existing database** — confirm before saying `y` at the prompt.

### Restore a specific full DB backup

```bash
docker compose ... exec server \
  python manage.py restore_backup \
  --file database/full/developeros-20260315-030000.sql.gz
```

### Restore an encrypted config snapshot

```bash
docker compose ... exec server \
  python manage.py restore_backup \
  --restore-config config/config-20260315-040000.tar.gz.enc
```

The decrypted tarball is extracted to a temp directory; copying its
contents to their final locations is manual.

## Known limitation: PITR is not currently achievable

The `--pitr` flag exists but **cannot do real point-in-time recovery**.

PostgreSQL PITR requires a *physical* base backup (`pg_basebackup`) plus
WAL replay. Our `run_full_backup` task uses `pg_dump`, which is
*logical* — a SQL script that recreates objects on a fresh cluster with
new LSNs and a different block layout. Replaying WAL onto a logically
restored database will corrupt it. Do not attempt this.

`--pitr` therefore prints a prominent warning, lists the closest
pre-target full backup and the WAL files after it (for inspection), and
recommends `--file` against the closest full backup as the supported
fallback. Data loss = time between that pg_dump and the target moment.

If real PITR is needed in production, the next step is to add a
`pg_basebackup`-based task to `apps/backup/tasks.py` and rewire `--pitr`
to use it. Tracking that as a follow-up rather than a blocker.

## Drills

> A backup is only as good as the last successful restore drill.

Suggested cadence: **quarterly**, alternating between:

1. Restore latest full to a scratch staging environment, run the test
   suite, verify the most recent updates are present.
2. Restore an encrypted config snapshot to a scratch directory and
   confirm the contents decrypt and tar-extract cleanly.

Record each drill in a brief log (timestamp, who ran it, what type,
outcome, duration) — either in `BackupLog`-style rows or in this file's
"Drill log" section below.

### Drill log

| Date | Operator | Type | Outcome | RTO observed | Notes |
|------|----------|------|---------|--------------|-------|
| _none yet_ | | | | | |

## Incident playbook (stub)

When the prod database is suspected lost or corrupted:

1. **Stop writes.** Pause Celery workers and put the API in maintenance
   (block at NPM / nginx).
2. **Triage.** Is the DB up but corrupt, or is the volume gone? Different
   recovery paths.
3. **Decide RTO target.** If business needs full-history recovery, you're
   restoring the latest pg_dump (data loss = up to 24 h, since full
   backups are daily). If you accept losing only a few minutes, that
   requires PITR — which today is not implemented (see above).
4. **Restore.**
   ```bash
   docker compose ... exec server python manage.py restore_backup --latest
   ```
5. **Validate.** Run the smoke-test suite, sample-query a recent record
   you remember writing, check `BackupLog` is consistent.
6. **Resume traffic.** Unpause Celery, lift maintenance.
7. **Post-mortem.** Within 5 working days, in `docs/postmortems/`.

## Security follow-ups

- The previous version of this file leaked the database password
  `devOS2024secure` into git history (line 11 of the prior content).
  **Action:** rotate the password if it has not already been changed,
  and consider expunging it from history with `git filter-repo` or BFG
  + force-push (coordinate with everyone else who has the repo cloned
  before doing this).
- The `BACKUP_SECRETS_DIR` is included in the encrypted config snapshot;
  the encryption key is derived from `SECRET_KEY`. If `SECRET_KEY`
  rotates, **older config backups become undecryptable**. Plan
  `SECRET_KEY` rotations carefully or maintain an out-of-band copy of
  prior keys.
- `restore_backup --latest` does no integrity check beyond gzip.
  Consider adding a SHA-256 checksum recorded alongside each upload.
