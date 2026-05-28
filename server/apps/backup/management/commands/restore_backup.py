"""
Management command to list and restore backups from Backblaze B2.

Usage:
    python manage.py restore_backup --list
    python manage.py restore_backup --list --type full
    python manage.py restore_backup --latest
    python manage.py restore_backup --file database/full/developeros-20260315-030000.sql.gz
    python manage.py restore_backup --pitr "2026-03-15 14:30"
    python manage.py restore_backup --restore-config config/config-20260315-040000.tar.gz.enc
"""

import gzip
import os
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.backup import b2_client
from apps.backup.tasks import _decrypt_file, _get_db_password


class Command(BaseCommand):
    help = "List and restore backups from Backblaze B2"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--list", action="store_true", help="List available backups")
        group.add_argument("--latest", action="store_true", help="Restore latest full DB backup")
        group.add_argument("--file", type=str, help="Restore a specific backup by B2 key")
        group.add_argument("--pitr", type=str, help="Point-in-time recovery (ISO timestamp)")
        group.add_argument("--restore-config", type=str, help="Decrypt and extract a config backup")

        parser.add_argument(
            "--type",
            choices=["full", "wal", "media", "config"],
            help="Filter --list by backup type",
        )
        parser.add_argument(
            "--yes", "-y",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, **options):
        if options["list"]:
            self._handle_list(options.get("type"))
        elif options["latest"]:
            self._handle_restore_latest(options["yes"])
        elif options["file"]:
            self._handle_restore_file(options["file"], options["yes"])
        elif options["pitr"]:
            self._handle_pitr(options["pitr"], options["yes"])
        elif options["restore_config"]:
            self._handle_restore_config(options["restore_config"], options["yes"])

    # ── List ────────────────────────────────────────────────────────────

    def _handle_list(self, backup_type: str | None):
        prefix_map = {
            "full": "database/full/",
            "wal": "database/wal/",
            "media": "media/",
            "config": "config/",
        }

        if backup_type:
            prefixes = {backup_type: prefix_map[backup_type]}
        else:
            prefixes = prefix_map

        for btype, prefix in prefixes.items():
            objects = b2_client.list_objects(prefix)
            if not objects:
                self.stdout.write(f"\n  {btype.upper()}: (empty)")
                continue

            self.stdout.write(f"\n  {btype.upper()} ({len(objects)} files):")
            # Show newest first, limit to 20
            objects.sort(key=lambda o: o["LastModified"], reverse=True)
            for obj in objects[:20]:
                size_mb = obj["Size"] / (1024 * 1024)
                date_str = obj["LastModified"].strftime("%Y-%m-%d %H:%M UTC")
                self.stdout.write(f"    {obj['Key']}  ({size_mb:.1f} MB, {date_str})")
            if len(objects) > 20:
                self.stdout.write(f"    ... and {len(objects) - 20} more")

        self.stdout.write("")

    # ── Restore latest full backup ──────────────────────────────────────

    def _handle_restore_latest(self, skip_confirm: bool):
        objects = b2_client.list_objects("database/full/")
        if not objects:
            raise CommandError("No full backups found on B2.")

        objects.sort(key=lambda o: o["LastModified"], reverse=True)
        latest = objects[0]
        self._handle_restore_file(latest["Key"], skip_confirm)

    # ── Restore specific file ───────────────────────────────────────────

    def _handle_restore_file(self, b2_key: str, skip_confirm: bool):
        if not b2_key.startswith("database/full/"):
            raise CommandError(f"Expected a database/full/ key, got: {b2_key}")

        self.stdout.write(f"\n  Restoring: {b2_key}")

        if not skip_confirm:
            confirm = input("  This will OVERWRITE the current database. Continue? [y/N] ")
            if confirm.lower() != "y":
                self.stdout.write("  Aborted.")
                return

        tmp_gz = Path(tempfile.gettempdir()) / "restore-backup.sql.gz"
        tmp_sql = Path(tempfile.gettempdir()) / "restore-backup.sql"

        try:
            self.stdout.write("  Downloading...")
            b2_client.download_file(b2_key, tmp_gz)

            self.stdout.write("  Decompressing...")
            with gzip.open(tmp_gz, "rb") as gz, open(tmp_sql, "wb") as out:
                while True:
                    chunk = gz.read(8192)
                    if not chunk:
                        break
                    out.write(chunk)

            db_host = os.environ.get("DB_HOST", "db")
            db_user = os.environ.get("DB_USER", "postgres")
            db_name = os.environ.get("DB_NAME", "developerOS")
            db_port = os.environ.get("DB_PORT", "5432")

            self.stdout.write(f"  Restoring to {db_name}@{db_host}...")
            result = subprocess.run(
                [
                    "psql",
                    "-h", db_host,
                    "-U", db_user,
                    "-p", db_port,
                    "-d", db_name,
                    "-f", str(tmp_sql),
                ],
                env={**os.environ, "PGPASSWORD": _get_db_password()},
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                self.stderr.write(f"  psql errors:\n{result.stderr}")
            else:
                self.stdout.write(self.style.SUCCESS("  Restore completed successfully."))

        finally:
            for p in (tmp_gz, tmp_sql):
                if p.exists():
                    p.unlink()

    # ── Point-in-time recovery (NOT CURRENTLY ACHIEVABLE) ──────────────
    #
    # True PostgreSQL PITR requires a *physical* base backup produced by
    # pg_basebackup, plus continuous WAL archiving onto that physical
    # cluster. Our run_full_backup task uses pg_dump, which is *logical*
    # — a SQL script that recreates objects but on a fresh cluster with
    # different LSNs and block layout. WAL records cannot be replayed
    # onto a logically-restored database; doing so corrupts the cluster.
    #
    # Until a pg_basebackup task is added, --pitr cannot do real PITR.
    # We keep the flag so it does something safe: discover and download
    # the relevant artifacts so a Platform Operator can inspect them
    # (and manually attempt recovery if they understand the trade-offs),
    # but we refuse to print the broken "restore pg_dump then replay
    # WAL" recipe that the previous version emitted.

    def _handle_pitr(self, target_time_str: str, skip_confirm: bool):
        try:
            target_time = datetime.fromisoformat(target_time_str)
        except ValueError:
            raise CommandError(f"Invalid timestamp: {target_time_str}. Use ISO format: 2026-03-15 14:30")

        # Find the latest full backup BEFORE target time
        full_objects = b2_client.list_objects("database/full/")
        candidates = [
            o for o in full_objects
            if o["LastModified"].replace(tzinfo=None) <= target_time
        ]
        if not candidates:
            raise CommandError(f"No full backup found before {target_time_str}")

        candidates.sort(key=lambda o: o["LastModified"], reverse=True)
        base_backup = candidates[0]

        # Find WAL files between base backup time and target time
        wal_objects = b2_client.list_objects("database/wal/")
        wal_files = [
            o for o in wal_objects
            if base_backup["LastModified"] <= o["LastModified"]
        ]
        wal_files.sort(key=lambda o: o["Key"])

        self.stdout.write("\n" + self.style.WARNING(
            "  ⚠  TRUE POINT-IN-TIME RECOVERY IS NOT IMPLEMENTED."
        ))
        self.stdout.write(
            "  Our database backups are pg_dump (logical) snapshots, not\n"
            "  pg_basebackup (physical). PostgreSQL WAL replay only works onto\n"
            "  a physical cluster — replaying WAL onto a pg_dump restore will\n"
            "  corrupt the database. To get real PITR, the run_full_backup\n"
            "  task needs to be replaced with pg_basebackup.\n"
        )

        self.stdout.write("  What this command can offer right now:\n")
        self.stdout.write(f"    Closest pg_dump before {target_time_str}:")
        self.stdout.write(f"      {base_backup['Key']}")
        self.stdout.write(f"      ({base_backup['LastModified'].strftime('%Y-%m-%d %H:%M UTC')})")
        self.stdout.write(f"    WAL segments archived after that pg_dump: {len(wal_files)}")
        self.stdout.write("")
        self.stdout.write("  Recommended next steps:\n")
        self.stdout.write("    A) For a best-effort restore (data loss = time between the")
        self.stdout.write("       pg_dump above and your target), run:")
        self.stdout.write(f"         python manage.py restore_backup --file {base_backup['Key']}")
        self.stdout.write("    B) If you need real PITR, do not use this command. Implement")
        self.stdout.write("       pg_basebackup-based backups first; until then PITR is not")
        self.stdout.write("       a recovery option.\n")

        if not skip_confirm:
            confirm = input(
                "  Download the base pg_dump + WAL segments locally for inspection? [y/N] "
            )
            if confirm.lower() != "y":
                self.stdout.write("  Nothing downloaded.")
                return

        tmp_dir = Path(tempfile.mkdtemp(prefix="pitr-inspect-"))
        tmp_gz = tmp_dir / "base.sql.gz"

        self.stdout.write("\n  Downloading base pg_dump...")
        b2_client.download_file(base_backup["Key"], tmp_gz)

        wal_dir = tmp_dir / "wal"
        wal_dir.mkdir()
        self.stdout.write(f"  Downloading {len(wal_files)} WAL files...")
        for wal_obj in wal_files:
            wal_name = Path(wal_obj["Key"]).name
            b2_client.download_file(wal_obj["Key"], wal_dir / wal_name)

        self.stdout.write(self.style.SUCCESS(f"\n  Files downloaded to: {tmp_dir}"))
        self.stdout.write(
            "  These are for inspection only. Do not attempt to combine them\n"
            "  via 'restore pg_dump then replay WAL' — that will corrupt the\n"
            "  database. See backup-restore.md for the supported recovery flow.\n"
        )

    # ── Restore config ──────────────────────────────────────────────────

    def _handle_restore_config(self, b2_key: str, skip_confirm: bool):
        if not b2_key.startswith("config/"):
            raise CommandError(f"Expected a config/ key, got: {b2_key}")

        self.stdout.write(f"\n  Restoring config: {b2_key}")

        if not skip_confirm:
            confirm = input("  Decrypt and extract config backup? [y/N] ")
            if confirm.lower() != "y":
                self.stdout.write("  Aborted.")
                return

        tmp_enc = Path(tempfile.gettempdir()) / "config-restore.tar.gz.enc"
        tmp_tar = Path(tempfile.gettempdir()) / "config-restore.tar.gz"
        extract_dir = Path(tempfile.gettempdir()) / "config-restore"

        try:
            self.stdout.write("  Downloading...")
            b2_client.download_file(b2_key, tmp_enc)

            self.stdout.write("  Decrypting...")
            _decrypt_file(tmp_enc, tmp_tar)

            self.stdout.write("  Extracting...")
            extract_dir.mkdir(exist_ok=True)
            with tarfile.open(tmp_tar, "r:gz") as tar:
                tar.extractall(path=extract_dir)

            self.stdout.write(self.style.SUCCESS(f"\n  Config extracted to: {extract_dir}"))
            self.stdout.write("  Contents:")
            for item in sorted(extract_dir.rglob("*")):
                if item.is_file():
                    self.stdout.write(f"    {item.relative_to(extract_dir)}")

            self.stdout.write("\n  Copy files to their target locations manually.")
            self.stdout.write(f"  Clean up {extract_dir} when done.\n")

        finally:
            for p in (tmp_enc, tmp_tar):
                if p.exists():
                    p.unlink()
