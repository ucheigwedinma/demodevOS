"""Celery tasks for automated backups to Backblaze B2."""

import base64
import gzip
import logging
import os
import subprocess
import tarfile
import tempfile
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.utils import timezone

from . import b2_client
from .models import BackupLog

logger = logging.getLogger(__name__)

FULL_BACKUP_RETRY_BASE = 60  # seconds
FULL_BACKUP_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Encryption helpers (for config backups)
# ---------------------------------------------------------------------------

def _derive_fernet_key() -> bytes:
    """Derive a Fernet key from Django SECRET_KEY via PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"developeros-config-backup-salt",
        iterations=480_000,
    )
    key = kdf.derive(settings.SECRET_KEY.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


def _encrypt_file(source_path: Path, dest_path: Path) -> None:
    """Encrypt a file with Fernet (AES-128-CBC under the hood)."""
    f = Fernet(_derive_fernet_key())
    data = source_path.read_bytes()
    dest_path.write_bytes(f.encrypt(data))


def _decrypt_file(source_path: Path, dest_path: Path) -> None:
    """Decrypt a Fernet-encrypted file."""
    f = Fernet(_derive_fernet_key())
    data = source_path.read_bytes()
    dest_path.write_bytes(f.decrypt(data))


# ---------------------------------------------------------------------------
# Task 1: Full database backup (daily)
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    max_retries=FULL_BACKUP_MAX_RETRIES,
    acks_late=True,
)
def run_full_backup(self):
    """pg_dump → gzip → upload to B2 database/full/."""
    now = timezone.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    filename = f"developeros-{timestamp}.sql.gz"
    b2_key = f"database/full/{filename}"

    log = BackupLog.objects.create(
        backup_type=BackupLog.BackupType.FULL,
        status=BackupLog.Status.STARTED,
        file_name=filename,
        started_at=now,
    )

    tmp_path = Path(tempfile.gettempdir()) / filename

    try:
        # pg_dump → gzip
        db_host = os.environ.get("DB_HOST", "db")
        db_user = os.environ.get("DB_USER", "postgres")
        db_name = os.environ.get("DB_NAME", "developerOS")
        db_port = os.environ.get("DB_PORT", "5432")

        logger.info("backup.full.start file=%s", filename)

        with open(tmp_path, "wb") as f:
            dump = subprocess.Popen(
                [
                    "pg_dump",
                    "-h", db_host,
                    "-U", db_user,
                    "-p", db_port,
                    "-d", db_name,
                    "--no-owner",
                    "--no-acl",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "PGPASSWORD": _get_db_password()},
            )
            with gzip.open(f, "wb") as gz:
                while True:
                    chunk = dump.stdout.read(8192)
                    if not chunk:
                        break
                    gz.write(chunk)

            dump.wait()
            if dump.returncode != 0:
                stderr = dump.stderr.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"pg_dump failed (exit {dump.returncode}): {stderr}")

        # Verify gzip integrity
        with gzip.open(tmp_path, "rb") as gz:
            while gz.read(8192):
                pass

        file_size = tmp_path.stat().st_size

        # Upload
        log.status = BackupLog.Status.UPLOADING
        log.save(update_fields=["status"])

        b2_client.upload_file(tmp_path, b2_key)

        # Complete
        log.status = BackupLog.Status.COMPLETED
        log.b2_path = b2_key
        log.size_bytes = file_size
        log.completed_at = timezone.now()
        log.metadata = {
            "db_host": db_host,
            "db_name": db_name,
            "duration_seconds": (timezone.now() - now).total_seconds(),
        }
        log.save(update_fields=["status", "b2_path", "size_bytes", "completed_at", "metadata"])

        logger.info("backup.full.completed file=%s size=%d", filename, file_size)

    except Exception as exc:
        log.status = BackupLog.Status.FAILED
        log.error_message = str(exc)[:4000]
        log.completed_at = timezone.now()
        log.save(update_fields=["status", "error_message", "completed_at"])

        logger.exception("backup.full.failed file=%s", filename)

        countdown = min(FULL_BACKUP_RETRY_BASE * (2 ** self.request.retries), 600)
        raise self.retry(exc=exc, countdown=countdown)

    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return {"file": filename, "b2_key": b2_key, "size": log.size_bytes}


# ---------------------------------------------------------------------------
# Task 2: Upload WAL archives (hourly)
# ---------------------------------------------------------------------------

@shared_task
def upload_wal_archives():
    """Scan WAL archive directory, upload segments to B2, delete local copies."""
    wal_dir = Path(settings.BACKUP_WAL_DIR)
    if not wal_dir.exists():
        logger.info("backup.wal.skip reason=wal_dir_missing path=%s", wal_dir)
        return {"uploaded": 0, "reason": "wal_dir_missing"}

    today = timezone.now().strftime("%Y%m%d")
    uploaded = 0
    errors = 0

    for wal_file in sorted(wal_dir.iterdir()):
        if not wal_file.is_file():
            continue
        # Skip non-WAL files (e.g. .history, .backup)
        if wal_file.suffix in (".history", ".backup", ".partial"):
            continue

        b2_key = f"database/wal/{today}/{wal_file.name}"
        now = timezone.now()
        log = BackupLog.objects.create(
            backup_type=BackupLog.BackupType.WAL,
            status=BackupLog.Status.UPLOADING,
            file_name=wal_file.name,
            started_at=now,
        )

        try:
            size = b2_client.upload_file(wal_file, b2_key)
            wal_file.unlink()

            log.status = BackupLog.Status.COMPLETED
            log.b2_path = b2_key
            log.size_bytes = size
            log.completed_at = timezone.now()
            log.save(update_fields=["status", "b2_path", "size_bytes", "completed_at"])

            uploaded += 1

        except Exception as exc:
            log.status = BackupLog.Status.FAILED
            log.error_message = str(exc)[:4000]
            log.completed_at = timezone.now()
            log.save(update_fields=["status", "error_message", "completed_at"])
            logger.exception("backup.wal.failed file=%s", wal_file.name)
            errors += 1

    logger.info("backup.wal.done uploaded=%d errors=%d", uploaded, errors)
    return {"uploaded": uploaded, "errors": errors}


# ---------------------------------------------------------------------------
# Task 3: Sync media uploads (daily)
# ---------------------------------------------------------------------------

@shared_task
def sync_media_backup():
    """Walk /app/media/, upload new/changed files to B2 media/ prefix."""
    media_root = Path(settings.MEDIA_ROOT)
    if not media_root.exists():
        logger.info("backup.media.skip reason=media_root_missing")
        return {"uploaded": 0, "skipped": 0}

    now = timezone.now()
    log = BackupLog.objects.create(
        backup_type=BackupLog.BackupType.MEDIA,
        status=BackupLog.Status.STARTED,
        file_name=f"media-sync-{now.strftime('%Y%m%d-%H%M%S')}",
        started_at=now,
    )

    uploaded = 0
    skipped = 0
    total_size = 0

    try:
        for file_path in media_root.rglob("*"):
            if not file_path.is_file():
                continue

            relative = file_path.relative_to(media_root)
            b2_key = f"media/{relative}"

            # Check if file already exists with same size (simple sync)
            existing = b2_client.head_object(b2_key)
            if existing and existing.get("ContentLength") == file_path.stat().st_size:
                skipped += 1
                continue

            size = b2_client.upload_file(file_path, b2_key)
            uploaded += 1
            total_size += size

        log.status = BackupLog.Status.COMPLETED
        log.b2_path = "media/"
        log.size_bytes = total_size
        log.completed_at = timezone.now()
        log.metadata = {
            "uploaded": uploaded,
            "skipped": skipped,
            "duration_seconds": (timezone.now() - now).total_seconds(),
        }
        log.save(update_fields=["status", "b2_path", "size_bytes", "completed_at", "metadata"])

    except Exception as exc:
        log.status = BackupLog.Status.FAILED
        log.error_message = str(exc)[:4000]
        log.completed_at = timezone.now()
        log.metadata = {"uploaded": uploaded, "skipped": skipped}
        log.save(update_fields=["status", "error_message", "completed_at", "metadata"])
        logger.exception("backup.media.failed")
        raise

    logger.info("backup.media.done uploaded=%d skipped=%d size=%d", uploaded, skipped, total_size)
    return {"uploaded": uploaded, "skipped": skipped, "total_size": total_size}


# ---------------------------------------------------------------------------
# Task 4: Config snapshot (daily, encrypted)
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=FULL_BACKUP_MAX_RETRIES, acks_late=True)
def backup_config(self):
    """Tar secrets directory → AES encrypt → upload to B2 config/."""
    now = timezone.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    filename = f"config-{timestamp}.tar.gz.enc"
    b2_key = f"config/{filename}"

    secrets_dir = Path(settings.BACKUP_SECRETS_DIR)

    log = BackupLog.objects.create(
        backup_type=BackupLog.BackupType.CONFIG,
        status=BackupLog.Status.STARTED,
        file_name=filename,
        started_at=now,
    )

    tmp_tar = Path(tempfile.gettempdir()) / f"config-{timestamp}.tar.gz"
    tmp_enc = Path(tempfile.gettempdir()) / filename

    try:
        # Create tarball of secrets
        with tarfile.open(tmp_tar, "w:gz") as tar:
            if secrets_dir.exists():
                for item in secrets_dir.iterdir():
                    if item.is_file():
                        tar.add(str(item), arcname=f"secrets/{item.name}")

            # Also include .env.prod if it exists alongside compose file
            env_prod = Path("/app/.env.prod")
            if not env_prod.exists():
                env_prod = Path(settings.BASE_DIR).parent / ".env.prod"
            if env_prod.exists():
                tar.add(str(env_prod), arcname=".env.prod")

        # Encrypt
        _encrypt_file(tmp_tar, tmp_enc)

        file_size = tmp_enc.stat().st_size

        # Upload
        log.status = BackupLog.Status.UPLOADING
        log.save(update_fields=["status"])

        b2_client.upload_file(tmp_enc, b2_key)

        log.status = BackupLog.Status.COMPLETED
        log.b2_path = b2_key
        log.size_bytes = file_size
        log.completed_at = timezone.now()
        log.metadata = {
            "encrypted": True,
            "duration_seconds": (timezone.now() - now).total_seconds(),
        }
        log.save(update_fields=["status", "b2_path", "size_bytes", "completed_at", "metadata"])

        logger.info("backup.config.completed file=%s size=%d", filename, file_size)

    except Exception as exc:
        log.status = BackupLog.Status.FAILED
        log.error_message = str(exc)[:4000]
        log.completed_at = timezone.now()
        log.save(update_fields=["status", "error_message", "completed_at"])
        logger.exception("backup.config.failed file=%s", filename)
        countdown = min(FULL_BACKUP_RETRY_BASE * (2 ** self.request.retries), 600)
        raise self.retry(exc=exc, countdown=countdown)

    finally:
        for p in (tmp_tar, tmp_enc):
            if p.exists():
                p.unlink()

    return {"file": filename, "b2_key": b2_key, "size": file_size}


# ---------------------------------------------------------------------------
# Task 5: Cleanup old backups (weekly)
# ---------------------------------------------------------------------------

@shared_task
def cleanup_old_backups():
    """Delete old backups from B2 based on retention settings."""
    now = timezone.now()
    deleted_full = 0
    deleted_wal = 0
    deleted_config = 0

    full_cutoff = now - timedelta(days=settings.BACKUP_FULL_RETENTION_DAYS)
    wal_cutoff = now - timedelta(days=settings.BACKUP_WAL_RETENTION_DAYS)
    config_cutoff = now - timedelta(days=settings.BACKUP_CONFIG_RETENTION_DAYS)

    # Full database backups
    for obj in b2_client.list_objects("database/full/"):
        if obj["LastModified"] < full_cutoff:
            b2_client.delete_object(obj["Key"])
            deleted_full += 1

    # WAL archives
    for obj in b2_client.list_objects("database/wal/"):
        if obj["LastModified"] < wal_cutoff:
            b2_client.delete_object(obj["Key"])
            deleted_wal += 1

    # Config snapshots
    for obj in b2_client.list_objects("config/"):
        if obj["LastModified"] < config_cutoff:
            b2_client.delete_object(obj["Key"])
            deleted_config += 1

    logger.info(
        "backup.cleanup.done deleted_full=%d deleted_wal=%d deleted_config=%d",
        deleted_full, deleted_wal, deleted_config,
    )
    return {
        "deleted_full": deleted_full,
        "deleted_wal": deleted_wal,
        "deleted_config": deleted_config,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db_password() -> str:
    """Read the database password from Docker secret or env."""
    secret_path = Path("/run/secrets/db_password")
    if secret_path.is_file():
        return secret_path.read_text().strip()
    return os.environ.get("DB_PASSWORD", "postgres")
