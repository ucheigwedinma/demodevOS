# Scaling Checklist

Things to address as developerOS grows in tenants, users, and data volume.

---

## Django Admin

- [ ] Switch high-cardinality FK fields to `autocomplete_fields` (departments, projects, employees, users) — replaces full-table `<select>` with AJAX search
- [ ] Add `list_select_related` to admin classes with FK columns in `list_display` to reduce N+1 queries
- [ ] Consider read-only admin for audit/log models (security events, workflow audit events) to prevent accidental edits at scale

## Database

- [ ] Add composite indexes on `(organization, status)` and `(organization, created_at)` for tables that grow fastest (leads, tickets, journal entries, transactions)
- [ ] Partition large tables by organization or date range (inventory transactions, audit events, notification logs)
- [ ] Connection pooling — switch from direct PostgreSQL connections to PgBouncer
- [ ] Read replicas for reporting/analytics queries

## API Performance

- [ ] Audit `select_related` / `prefetch_related` on all ViewSet querysets — especially nested serializers
- [ ] Add pagination limits and enforce max page size across all endpoints
- [ ] Cache frequently-read, rarely-written data (org settings, platform editions, role permissions) with Redis
- [ ] Throttle per-org API rates to prevent a single tenant from starving others

## Multi-Tenancy

- [ ] Evaluate PostgreSQL Row-Level Security (RLS) policies as a database-level safety net — already initialized per-connection in signals
- [ ] Stress-test `OrgScopedMixin` and `OrgScopedAdminMixin` with 50+ orgs to verify no cross-tenant leaks under concurrent requests
- [ ] Audit all raw SQL / `.extra()` / `RawQuerySet` usage for org scoping gaps
- [ ] Consider per-tenant database schemas if regulatory requirements demand physical data isolation [django-tenant-schemas]

## Background Jobs (Celery)

- [ ] Add org-aware task routing — prevent one tenant's bulk import from blocking another's payroll run
- [ ] Set per-task time limits and retry policies
- [ ] Monitor queue depth per org

## Search

- [ ] Re-introduce Meilisearch (or Elasticsearch) when full-text search across documents, leads, and tickets becomes a bottleneck
- [ ] Index per-org to maintain tenant isolation at the search layer

## File Storage

- [ ] Move uploads to S3-compatible object storage with per-org prefixes
- [ ] Add file size limits and per-org storage quotas
- [ ] CDN for static assets and tenant file downloads

## Monitoring & Observability

- [ ] Per-org query count and latency dashboards (django-silk or OpenTelemetry)
- [ ] Slow query log with org context
- [ ] Alert on org-scoped data volume thresholds (e.g., org with 100k+ leads)

## MFA — Phase 2: SMS OTP & Hardware Keys

### SMS OTP

- [ ] Integrate SMS gateway (Twilio, AWS SNS, or similar) via `settings.SMS_PROVIDER` abstraction
- [ ] Add `phone_number` (E.164) and `phone_verified` fields to `UserProfile`
- [ ] Create phone verification flow (send code → confirm)
- [ ] Add `"sms"` method to `get_available_mfa_methods()` in `apps/accounts/mfa.py`
- [ ] Extend `VerifyOTPSerializer` to handle `method="sms"`
- [ ] Frontend: add SMS option to MFA method picker (login + settings)
- [ ] Rate limit per-phone and per-user to prevent SMS bombing
- [ ] Note: NIST SP 800-63B has deprecated SMS as a standalone authenticator (SIM-swap / SS7 risks) — offer as convenience fallback only, not primary

### Hardware Security Keys (FIDO2 / U2F)

- [ ] Extend existing WebAuthn passkey flow to explicitly support hardware keys (YubiKey, Titan, SoloKeys)
- [ ] Set `authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM` option for hardware-key-specific registration
- [ ] Add `device_type` field to `WebAuthnCredential` model (`platform` vs `cross-platform`) to distinguish passkeys from hardware keys in UI
- [ ] Frontend: separate "Hardware Key" section in MFA settings alongside "Passkeys"
- [ ] Allow naming hardware keys on registration (e.g. "Office YubiKey", "Backup Titan Key")
- [ ] Note: hardware keys are already technically supported via the passkey/WebAuthn flow — this phase adds explicit UX and management separation

## Secrets Management — Phase 2: Cloud Secrets Manager

- [ ] Migrate from Docker Compose file-based secrets to AWS Secrets Manager (or HashiCorp Vault)
- [ ] Implement secret rotation — auto-rotate `DJANGO_SECRET_KEY`, `DB_PASSWORD`, OAuth client secrets on a schedule
- [ ] Add `get_secret()` cloud provider backend in `config/secrets.py` (AWS SDK `boto3` → `secretsmanager.get_secret_value()`)
- [ ] Cache fetched secrets in-process with TTL to avoid per-request API calls
- [ ] Use IAM roles (not access keys) for ECS/EC2 instances to authenticate to Secrets Manager
- [ ] Audit trail — enable CloudTrail logging for all secret access events
- [ ] Note: current Docker Compose file-based secrets are sufficient for single-VPS; cloud secrets manager becomes valuable at multi-node / ECS / Kubernetes scale

## File Uploads — Phase 2: Auth-Gated Media Serving

- [ ] Nginx currently serves `/media/` publicly without authentication — all uploaded files (HR docs, contracts, tickets) are accessible to anyone with the URL
- [ ] Option A: Use nginx `internal;` directive + Django `X-Accel-Redirect` — Django view checks auth/org scoping, returns `X-Accel-Redirect` header, nginx serves the file
- [ ] Option B: Move uploads to S3 with pre-signed URLs (time-limited, per-user) — eliminates local file serving entirely
- [ ] Add `Content-Disposition: attachment` header to force download (prevents browser rendering of malicious HTML/SVG)
- [ ] Enable `access_log` on nginx `/media/` location (currently `off`)
- [ ] Consider ClamAV virus scanning on upload before storage

## Frontend

- [ ] Lazy-load heavy routes (document repository, project execution views)
- [ ] Virtual scrolling for large tables (already using @tanstack/svelte-table — enable row virtualization)
- [ ] Service worker caching for static assets
- [ ] Consider per-org CDN subdomains if white-labeling is needed


Tenant isolation
RBAC
MFA
audit logging
encrypted storage
zero-trust network policies
