"""
Base Django settings for the Real Estate Developer Management Platform.
"""

import os
from datetime import timedelta
from pathlib import Path

from config.secrets import get_secret

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = get_secret(
    "django_secret_key",
    env_var="DJANGO_SECRET_KEY",
    default="insecure-dev-key-do-not-use-in-production-abc123xyz789",
)

DEBUG = False

ALLOWED_HOSTS = []

# --- Installed Apps ---

DJANGO_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "daphne",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "channels",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "django_celery_beat",
    "drf_spectacular",
    "auditlog",
    "guardian",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.properties",
    "apps.projects",
    "apps.finance",
    "apps.crm",
    "apps.partners",
    "apps.tenants",
    "apps.documents",
    "apps.compliance",
    "apps.valuations",
    "apps.analytics",
    "apps.procurement",
    "apps.inventory",
    "apps.hr",
    "apps.settings",
    "apps.notifications",
    "apps.workflows",
    "apps.support_desk",
    "apps.facility_management",
    "apps.search",
    "apps.backup",
    "apps.meetings",
    "apps.workspace",
    "apps.calendar",
    "apps.internal_tasks",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --- Middleware ---

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.AdminProtectionMiddleware",
    "apps.accounts.middleware.OrganizationMiddleware",
    # Cluster 4: per-org access-policy enforcement. Fail-open by design;
    # skips a hard-coded allowlist of paths (auth, admin, health) so a
    # buggy deny-policy can never lock anyone out of recovery.
    "apps.accounts.policy_middleware.AccessPolicyMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "csp.middleware.CSPMiddleware",
    "django_permissions_policy.PermissionsPolicyMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "developerOS"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": get_secret("db_password", env_var="DB_PASSWORD", default="postgres"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "600")),
        "OPTIONS": {
            "connect_timeout": 5,
        },
    }
}

# Require SSL for the DB connection when DB_SSLMODE is set (e.g. managed DB)
_db_sslmode = os.environ.get("DB_SSLMODE")
if _db_sslmode:
    DATABASES["default"]["OPTIONS"]["sslmode"] = _db_sslmode

# --- Auth ---

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    # Always-on baseline (used at registration when no user/org exists yet)
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.password_validators.UppercaseValidator"},
    {"NAME": "apps.accounts.password_validators.LowercaseValidator"},
    {"NAME": "apps.accounts.password_validators.SpecialCharacterValidator"},
    {"NAME": "apps.accounts.password_validators.MaxLengthValidator"},
    # Policy-aware (no-ops without a user; active on password change /
    # set-password flows where the caller passes user). Reads from
    # Organization.password_* fields edited at /iam/auth.
    {"NAME": "apps.accounts.password_validators.OrganizationPasswordPolicyValidator"},
    {"NAME": "apps.accounts.password_validators.PasswordHistoryValidator"},
]

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "apps.settings.auth_backend.RbacBackend",
    "guardian.backends.ObjectPermissionBackend",
)

# --- WebAuthn / Passkeys ---

WEBAUTHN_RP_ID = os.environ.get("WEBAUTHN_RP_ID", "localhost")
WEBAUTHN_RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "developerOS")
WEBAUTHN_ORIGIN = os.environ.get("WEBAUTHN_ORIGIN", "http://localhost:5173")

# --- Session Protection ---

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# --- Content Security Policy (django-csp) ---

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-eval'", "'unsafe-inline'"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "blob:", "https://api.maptiler.com"],
        "connect-src": ["'self'", "https://api.maptiler.com"],
        "worker-src": ["'self'", "blob:"],
        "frame-ancestors": ["'self'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    },
}

# --- Permissions Policy ---

PERMISSIONS_POLICY = {
    "accelerometer": [],
    "camera": [],
    "geolocation": [],
    "gyroscope": [],
    "magnetometer": [],
    "microphone": [],
    "usb": [],
}

# --- Internationalization ---

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_CURRENCY_CODE = os.environ.get("DEFAULT_CURRENCY_CODE", "").strip().upper()

# --- Static / Media ---

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Unfold Admin Theme ---

UNFOLD = {
    "SITE_TITLE": "developerOS Admin",
    "SITE_HEADER": "developerOS",
    "SITE_URL": "/",
    "COLORS": {
        "primary": {
            "50": "250 250 250",
            "100": "245 245 245",
            "200": "229 229 229",
            "300": "212 212 212",
            "400": "163 163 163",
            "500": "115 115 115",
            "600": "82 82 82",
            "700": "64 64 64",
            "800": "38 38 38",
            "900": "23 23 23",
            "950": "10 10 10",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
    },
}

# --- DRF ---

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.SessionAwareJWTAuthentication",
        "apps.accounts.authentication.APIKeyAuthentication",
        "apps.accounts.authentication.ApplicationTokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/minute",
        "user": "600/minute",
        "auth": "5/minute",
        "otp": "5/minute",
        "password_reset": "3/minute",
        "mfa_management": "10/minute",
        "sensitive_action": "5/minute",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

# --- Simple JWT ---

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# --- DRF Spectacular ---

SPECTACULAR_SETTINGS = {
    "TITLE": "DeveloperOS API",
    "DESCRIPTION": "Real Estate Developer Management Platform API",
    "VERSION": "0.1.0",
}

# --- CORS ---

CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:5177",
).split(",")

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:5177",
]

# --- Channels (WebSocket) ---

ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379/2")],
        },
    },
}

# --- Celery ---

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    # ── Platform tasks ──────────────────────────────────────────────────
    "critical-notification-checks": {
        "task": "notifications.run_critical_notification_checks",
        "schedule": 3600,  # Every 1 hour
    },
    "hr-scheduled-workflows": {
        "task": "apps.hr.tasks.run_hr_scheduled_workflows",
        "schedule": 900,  # Every 15 minutes
    },
    "scheduled-report-delivery": {
        "task": "apps.settings.tasks.run_scheduled_reports",
        "schedule": 3600,  # Every 1 hour
    },

    # ── Backups (apps.backup.tasks) ─────────────────────────────────────
    # Defined here so Beat schedules them by default in every environment.
    # DatabaseScheduler will sync these into django_celery_beat tables on
    # startup; later edits in /admin/ override these defaults.
    "backup-database-full": {
        "task": "apps.backup.tasks.run_full_backup",
        "schedule": crontab(hour=3, minute=0),  # Daily 03:00 UTC
    },
    "backup-wal-upload": {
        "task": "apps.backup.tasks.upload_wal_archives",
        "schedule": 900,  # Every 15 min — bounds RPO at ~15 min
    },
    "backup-media-sync": {
        "task": "apps.backup.tasks.sync_media_backup",
        "schedule": crontab(hour=4, minute=0),  # Daily 04:00 UTC
    },

    # ── Workspace teams (apps.workspace.tasks) ──────────────────────────
    # Run hourly: each invocation checks every org, dispatches digests for
    # those at 08:00 local time. One schedule covers all timezones.
    "workspace-team-digests": {
        "task": "workspace.send_team_digests",
        "schedule": crontab(minute=5),  # On the 5th minute of every hour
    },

    # ── Calendar reminders (apps.calendar.tasks) ────────────────────────
    # Per design §10: every minute, scan for events whose reminder window
    # just elapsed and dispatch via apps.notifications.services.
    "calendar-dispatch-due-reminders": {
        "task": "calendar.dispatch_due_reminders",
        "schedule": 60.0,  # Every minute
    },

    # ── Internal Tasks reminders (apps.internal_tasks.tasks) ───────────────
    # Per design §10: every 15 minutes, dispatch 9am-local reminders for
    # tasks due tomorrow + due today. Idempotency via 23h Notification lookback.
    "internal-tasks-due-reminders": {
        "task": "internal_tasks.dispatch_due_reminders",
        "schedule": 900.0,  # Every 15 minutes
    },
    "backup-config-snapshot": {
        "task": "apps.backup.tasks.backup_config",
        "schedule": crontab(hour=4, minute=30),  # Daily 04:30 UTC
    },
    "backup-cleanup-old": {
        "task": "apps.backup.tasks.cleanup_old_backups",
        "schedule": crontab(hour=5, minute=0, day_of_week=0),  # Sunday 05:00 UTC
    },

    # ── IAM ─────────────────────────────────────────────────────────────
    "iam-sweep-expired-access-grants": {
        "task": "apps.accounts.tasks.sweep_expired_access_grants",
        "schedule": crontab(hour=6, minute=0),  # Daily 06:00 UTC
    },
}

# --- Backup (Backblaze B2) ---

from config.secrets import get_secret  # noqa: E402

B2_KEY_ID = get_secret("b2_key_id")
B2_APP_KEY = get_secret("b2_app_key")
B2_BUCKET_NAME = get_secret("b2_bucket_name", default="")
B2_ENDPOINT = get_secret("b2_endpoint", default="")
BACKUP_WAL_DIR = os.environ.get("BACKUP_WAL_DIR", "/wal_archive")
BACKUP_SECRETS_DIR = os.environ.get("BACKUP_SECRETS_DIR", "/app/secrets")
BACKUP_FULL_RETENTION_DAYS = 30
BACKUP_WAL_RETENTION_DAYS = 7
BACKUP_CONFIG_RETENTION_DAYS = 30

# --- Email ---

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = get_secret("email_host_password", env_var="EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "developerOS <noreply@developeros.io>")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5176")

# --- Cache ---

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
    }
}

# --- Document Search ---

DOCUMENT_OCR_ENABLED = os.environ.get("DOCUMENT_OCR_ENABLED", "False") == "True"
DOCUMENT_OCR_LANG = os.environ.get("DOCUMENT_OCR_LANG", "eng")
DOCUMENT_OCR_DPI = int(os.environ.get("DOCUMENT_OCR_DPI", "220"))
DOCUMENT_OCR_MAX_PAGES = int(os.environ.get("DOCUMENT_OCR_MAX_PAGES", "20"))

# Optional base URLs for provider-specific signing portals.
DOCUMENT_ESIGN_DOCUSIGN_SIGNING_BASE_URL = os.environ.get(
    "DOCUMENT_ESIGN_DOCUSIGN_SIGNING_BASE_URL",
    "",
)
DOCUMENT_ESIGN_ADOBE_SIGNING_BASE_URL = os.environ.get(
    "DOCUMENT_ESIGN_ADOBE_SIGNING_BASE_URL",
    "",
)
DOCUMENT_ESIGN_DROPBOX_SIGNING_BASE_URL = os.environ.get(
    "DOCUMENT_ESIGN_DROPBOX_SIGNING_BASE_URL",
    "",
)
DOCUMENT_ESIGN_SIGNNOW_SIGNING_BASE_URL = os.environ.get(
    "DOCUMENT_ESIGN_SIGNNOW_SIGNING_BASE_URL",
    "",
)

# ---------------------------------------------------------------------------
# OAuth Providers (Federated Login)
# ---------------------------------------------------------------------------
OAUTH_PROVIDERS = {
    "google": {
        "client_id": get_secret("oauth_google_client_id", env_var="OAUTH_GOOGLE_CLIENT_ID"),
        "client_secret": get_secret("oauth_google_client_secret", env_var="OAUTH_GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.environ.get(
            "OAUTH_GOOGLE_REDIRECT_URI",
            f"{FRONTEND_URL}/login/oauth/callback",
        ),
    },
    "microsoft": {
        "client_id": get_secret("oauth_microsoft_client_id", env_var="OAUTH_MICROSOFT_CLIENT_ID"),
        "client_secret": get_secret("oauth_microsoft_client_secret", env_var="OAUTH_MICROSOFT_CLIENT_SECRET"),
        "tenant": os.environ.get("OAUTH_MICROSOFT_TENANT", "common"),
        "redirect_uri": os.environ.get(
            "OAUTH_MICROSOFT_REDIRECT_URI",
            f"{FRONTEND_URL}/login/oauth/callback",
        ),
    },
}
