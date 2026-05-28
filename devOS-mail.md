# developerOS Mail Service — Implementation Plan

> Multi-tenant email for organizations on the developerOS platform.
> Each org gets mailboxes under their own domain or a subdomain of `developeros.pro`.

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        INTERNET                                  │
│                                                                  │
│   MX → mail.developeros.pro (Mail VPS)                          │
│   HTTPS → app.developeros.pro (App VPS)                         │
└──────────┬──────────────────────────────┬────────────────────────┘
           │                              │
    ┌──────▼──────┐               ┌───────▼───────┐
    │  MAIL VPS   │   REST API    │   APP VPS     │
    │             │◄──────────────│               │
    │  Stalwart   │               │  Django API   │
    │  Mail       │   JMAP        │  SvelteKit UI │
    │  Server     │◄──────────────│  (Inbox)      │
    │             │               │               │
    │  Ports:     │               │  Ports:       │
    │  25 (SMTP)  │               │  8000 (API)   │
    │  465 (SMTPS)│               │  3000 (Client)│
    │  993 (IMAPS)│               │               │
    │  443 (HTTPS)│               │               │
    │  8080 (API) │               │               │
    └─────────────┘               └───────────────┘
```

**Two servers, strict separation:**

- **Mail VPS** — runs Stalwart only. Dedicated IP with clean reputation.
- **App VPS** — existing developerOS. Django provisions accounts via Stalwart REST API. SvelteKit renders the inbox UI via JMAP.

---

## 2. Infrastructure & Costs

### Mail VPS Requirements

| Resource       | Minimum    | Recommended (50 orgs) | Notes                              |
|----------------|------------|------------------------|-------------------------------------|
| CPU            | 1 vCPU     | 2 vCPU                 | Spam filtering is CPU-bound         |
| RAM            | 1 GB       | 2 GB                   | Stalwart is Rust — very efficient   |
| Disk           | 20 GB SSD  | 50 GB SSD              | ~100MB per active mailbox estimate  |
| OS             | Ubuntu 24  | Ubuntu 24              | Or Debian 12                        |
| Dedicated IPv4 | Required   | Required               | For PTR/rDNS record                 |

### Hosting Options

| Provider         | Spec               | Monthly Cost | Notes                                        |
|------------------|--------------------|-------------|----------------------------------------------|
| Hetzner CX22     | 2 vCPU, 4GB, 40GB  | €4.35       | Best value. EU datacenters.                  |
| Contabo Cloud S  | 4 vCPU, 8GB, 50GB  | €6.99       | More resources, US/EU/Asia.                  |
| Hostinger KVM 2  | 2 vCPU, 8GB, 100GB | $6.99       | Already using Hostinger for prod.            |
| DigitalOcean     | 1 vCPU, 2GB, 50GB  | $12.00      | Premium network, better deliverability rep.  |

**Recommended: Hetzner CX22 at ~$5/month** — best price/performance, excellent network reputation for mail.

### Total Monthly Cost

| Item                              | Cost        |
|-----------------------------------|-------------|
| Mail VPS                          | ~$5-7       |
| Domain (already owned)            | $0          |
| SSL (Let's Encrypt)               | $0          |
| Stalwart license                  | $0 (AGPL)   |
| DNS (Cloudflare free)             | $0          |
| Backups (B2 — existing)           | ~$0.50      |
| **Total**                         | **~$6-8/mo**|

---

## 3. Stalwart Mail Server

### Why Stalwart

- **Written in Rust** — low memory footprint, handles thousands of concurrent connections
- **All-in-one** — SMTP, IMAP, JMAP, ManageSieve in a single binary
- **Multi-tenant native** — domain-based account isolation, per-domain settings
- **REST API** — full account/domain provisioning via HTTP
- **JMAP support** — modern protocol for building custom webmail UIs (much better than IMAP for web clients)
- **Built-in spam filter** — sieve scripts, DNS blocklists, SPF/DKIM/DMARC validation
- **Storage flexibility** — SQLite, PostgreSQL, MySQL, S3-compatible blob storage
- **Open source** — AGPL v3, no enterprise paywall for core features
- **Docker-ready** — official image `stalwartlabs/mail-server`

### Docker Compose (Mail VPS)

```yaml
# /opt/mail/docker-compose.yml
services:
  stalwart:
    image: stalwartlabs/mail-server:latest
    container_name: stalwart
    restart: always
    ports:
      - "25:25"       # SMTP (inbound mail)
      - "465:465"     # SMTPS (outbound submission)
      - "587:587"     # SMTP submission (STARTTLS)
      - "993:993"     # IMAPS
      - "4190:4190"   # ManageSieve
      - "443:443"     # HTTPS (JMAP + webadmin)
      - "8080:8080"   # REST management API
    volumes:
      - stalwart-data:/opt/stalwart-mail
    environment:
      # Initial admin credentials (change after first login)
      STALWART_ADMIN_USER: admin
      STALWART_ADMIN_SECRET: "${STALWART_ADMIN_PASSWORD}"

volumes:
  stalwart-data:
```

### Storage Configuration

For multi-tenant at scale, configure Stalwart to use:
- **PostgreSQL** for account metadata, settings, indexes
- **S3 (Backblaze B2)** for message blob storage (already using B2 for backups)
- This keeps the VPS disk small while scaling storage cheaply

```toml
# /opt/stalwart-mail/etc/config.toml (excerpt)
[store."postgres"]
type = "postgresql"
url = "postgres://stalwart:password@localhost:5432/stalwart"

[store."s3"]
type = "s3"
bucket = "developeros-mail"
region = "us-east-005"
endpoint = "https://s3.us-east-005.backblazeb2.com"
access-key = "..."
secret-key = "..."

[storage]
data = "postgres"
blob = "s3"
lookup = "postgres"
directory = "postgres"
```

---

## 4. DNS Configuration

### For `developeros.pro` (platform domain)

```dns
; MX record — route mail to the mail server
@                  MX   10  mail.developeros.pro.

; A record for the mail server hostname
mail               A        <MAIL_VPS_IP>

; Reverse DNS (PTR) — set via VPS provider control panel
<MAIL_VPS_IP>      PTR      mail.developeros.pro.

; SPF — authorize the mail server to send
@                  TXT      "v=spf1 mx a:mail.developeros.pro ~all"

; DKIM — Stalwart generates the key, you publish it
dkim._domainkey    TXT      "v=DKIM1; k=rsa; p=<PUBLIC_KEY>"

; DMARC — policy for handling failures
_dmarc             TXT      "v=DMARC1; p=quarantine; rua=mailto:postmaster@developeros.pro; pct=100"

; Autoconfig/Autodiscover for mail clients
_autodiscover._tcp SRV      0 0 443 mail.developeros.pro.
autoconfig         CNAME    mail.developeros.pro.
```

### For Tenant Custom Domains (e.g. `acmecorp.com`)

Tenants who want `@acmecorp.com` mailboxes must add these DNS records:

```dns
@                  MX   10  mail.developeros.pro.
@                  TXT      "v=spf1 include:developeros.pro ~all"
dkim._domainkey    TXT      "<PROVIDED_BY_PLATFORM>"
_dmarc             TXT      "v=DMARC1; p=quarantine; rua=mailto:dmarc@developeros.pro"
```

The platform provides a DNS verification wizard (similar to how Google Workspace or Mailgun onboard domains).

---

## 5. Feature List

### Phase 1 — Core Mail (MVP)

**Backend (Django)**
- [ ] `MailDomain` model — org FK, domain name, verification status, DKIM keys, MX verified
- [ ] `Mailbox` model — org FK, email address, display name, quota, active status
- [ ] `MailAlias` model — source address → target mailbox(es)
- [ ] Provisioning service — create/update/delete domains and accounts via Stalwart REST API
- [ ] DNS verification job — check MX, SPF, DKIM, DMARC records for tenant domains
- [ ] Subdomain auto-provisioning — `orgslug.developeros.pro` domains created automatically
- [ ] Quota management — per-org and per-mailbox storage limits
- [ ] Signals — notify when domain verified, mailbox created, quota exceeded

**Frontend (SvelteKit) — Inbox UI**
- [ ] Inbox view — message list with sender, subject, date, read/unread status
- [ ] Message view — full email render (HTML sanitized + plain text fallback)
- [ ] Compose — rich text editor, to/cc/bcc, attachments
- [ ] Reply / Reply All / Forward
- [ ] Folders — Inbox, Sent, Drafts, Trash, Archive, custom folders
- [ ] Search — full-text search across mailbox
- [ ] Contacts integration — autocomplete from CRM contacts
- [ ] File attachments — upload/download, inline images

**Frontend — Admin (per org)**
- [ ] Domain management — add domain, DNS verification wizard, status indicators
- [ ] Mailbox management — create/edit/delete mailboxes for org members
- [ ] Alias management — create forwarding aliases
- [ ] Storage usage dashboard — per-mailbox and org-wide

**Frontend — Platform Admin (console)**
- [ ] All domains list with verification status
- [ ] All mailboxes with storage usage
- [ ] Delivery logs / bounce tracking
- [ ] Suspend/unsuspend org mail service
- [ ] Global storage quotas and limits

### Phase 2 — Enhanced

- [ ] Distribution lists / groups
- [ ] Shared mailboxes (e.g. `support@orgname.com` accessible by multiple users)
- [ ] Email signatures — org-level templates
- [ ] Auto-responders / out-of-office
- [ ] Sieve filter rules UI (move to folder, auto-label, forward)
- [ ] Calendar invites (iCal) rendering
- [ ] Mobile push notifications for new mail
- [ ] Spam/junk management UI (report spam, whitelist sender)

### Phase 3 — Advanced

- [ ] Email templates for org communications
- [ ] Scheduled send
- [ ] Read receipts
- [ ] Email analytics (sent/received/bounced per org)
- [ ] Data retention policies (auto-delete after N days)
- [ ] eDiscovery / compliance hold
- [ ] IMAP/SMTP credentials page (for native mail clients like Outlook/Thunderbird)
- [ ] S/MIME or PGP encryption support

---

## 6. Stalwart REST API — Key Endpoints

Base URL: `https://mail.developeros.pro:8080/api`

Authentication: HTTP Basic or Bearer token (admin credentials)

### Domain Management

```
POST   /api/domain/{domain_name}          Create domain
GET    /api/domain/{domain_name}          Get domain details
DELETE /api/domain/{domain_name}          Delete domain
GET    /api/domain                        List all domains
GET    /api/domain/{domain_name}/dkim     Get DKIM public key
```

### Account Management

```
POST   /api/account/{email}               Create account
GET    /api/account/{email}               Get account details
PATCH  /api/account/{email}               Update account
DELETE /api/account/{email}               Delete account
GET    /api/account                       List all accounts
```

### Account Creation Payload

```json
{
  "name": "John Doe",
  "secret": "initial_password_or_app_password",
  "email": ["john@acmecorp.com"],
  "quota": 1073741824,
  "type": "individual",
  "memberOf": [],
  "aliases": ["j.doe@acmecorp.com"]
}
```

---

## 7. JMAP — Building the Inbox UI

JMAP (JSON Meta Application Protocol) is the modern replacement for IMAP. It's HTTP-based, JSON-encoded, and designed for web/mobile clients.

**Endpoint:** `https://mail.developeros.pro/.well-known/jmap`

### Authentication
Each user authenticates with their mailbox credentials (email + password or app token). The SvelteKit client proxies JMAP requests through Django to avoid exposing the mail server directly.

### Key JMAP Methods

```
Email/query          — search/filter/sort messages
Email/get            — fetch full message (headers, body, attachments)
Email/set            — create draft, update flags (read/unread), move, delete
Email/changes        — get changes since last sync (push-like efficiency)
Mailbox/get          — list folders (Inbox, Sent, Drafts, etc.)
Mailbox/set          — create/rename/delete folders
EmailSubmission/set  — send an email
Thread/get           — conversation threading
SearchSnippet/get    — search result highlights
```

### Proxy Architecture

```
SvelteKit Inbox UI
       │
       │  fetch("/api/mail/jmap", { body: jmapRequest })
       ▼
Django REST endpoint (/api/mail/jmap/)
       │
       │  Authenticates user, resolves their JMAP credentials
       │  Proxies request to Stalwart JMAP endpoint
       ▼
Stalwart JMAP (https://mail.developeros.pro/.well-known/jmap)
       │
       │  Returns JSON response
       ▼
Django forwards response → SvelteKit renders inbox
```

This keeps Stalwart's JMAP port internal (not exposed to the internet) and lets Django enforce org-scoping and rate limiting.

---

## 8. Django Integration

### New App: `server/apps/mail/`

```
apps/mail/
├── __init__.py
├── models.py          # MailDomain, Mailbox, MailAlias
├── admin.py
├── serializers.py
├── views.py           # CRUD + JMAP proxy
├── urls.py
├── signals.py         # Auto-provision on org create
├── stalwart_client.py # REST API wrapper for Stalwart
├── dns_verification.py
├── tasks.py           # Celery: DNS checks, quota sync
└── migrations/
```

### Models

```python
class MailDomain(OrgScopedModel):
    domain = models.CharField(max_length=255, unique=True)
    is_subdomain = models.BooleanField(default=False)  # orgslug.developeros.pro
    mx_verified = models.BooleanField(default=False)
    spf_verified = models.BooleanField(default=False)
    dkim_verified = models.BooleanField(default=False)
    dmarc_verified = models.BooleanField(default=False)
    dkim_public_key = models.TextField(blank=True)
    status = models.CharField(...)  # pending, active, suspended
    provisioned_at = models.DateTimeField(null=True)

class Mailbox(OrgScopedModel):
    domain = models.ForeignKey(MailDomain, ...)
    user = models.ForeignKey(User, ..., null=True)  # linked platform user
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=255)
    quota_bytes = models.BigIntegerField(default=1_073_741_824)  # 1GB
    used_bytes = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)

class MailAlias(OrgScopedModel):
    source = models.EmailField()
    targets = models.ManyToManyField(Mailbox)
```

### Stalwart Client Service

```python
# apps/mail/stalwart_client.py
class StalwartClient:
    def __init__(self):
        self.base_url = settings.STALWART_API_URL  # https://mail-vps:8080/api
        self.auth = (settings.STALWART_ADMIN_USER, settings.STALWART_ADMIN_PASSWORD)

    def create_domain(self, domain: str) -> dict: ...
    def delete_domain(self, domain: str) -> None: ...
    def create_account(self, email, name, password, quota) -> dict: ...
    def update_account(self, email, **kwargs) -> dict: ...
    def delete_account(self, email) -> None: ...
    def get_dkim_key(self, domain: str) -> str: ...
```

---

## 9. SvelteKit Inbox UI

### Routes

```
/mail                      → Inbox (default folder)
/mail/folder/:name         → Specific folder view
/mail/compose              → New email
/mail/message/:id          → Read email
/mail/settings             → Mail settings (signature, auto-reply)
/mail/admin/domains        → Org admin: domain management
/mail/admin/mailboxes      → Org admin: mailbox management
```

### Key Components

```
components/mail/
├── MailLayout.svelte        # 3-column layout (folders | list | reader)
├── FolderList.svelte        # Sidebar folder tree
├── MessageList.svelte       # Email list with virtual scrolling
├── MessageRow.svelte        # Single email row (sender, subject, date)
├── MessageReader.svelte     # Full email view with HTML sanitization
├── ComposeDrawer.svelte     # Compose/reply drawer with rich text
├── AttachmentChip.svelte    # Attachment display/download
├── RecipientInput.svelte    # To/Cc/Bcc autocomplete
└── DnsVerificationWizard.svelte  # Domain setup guide
```

---

## 10. Security Considerations

- **JMAP proxy** — never expose Stalwart's JMAP/API ports to the public internet. All access goes through Django.
- **HTML sanitization** — sanitize all email HTML before rendering (XSS prevention). Use DOMPurify on the client.
- **Attachment scanning** — consider ClamAV integration in Stalwart for malware scanning.
- **Rate limiting** — limit outbound emails per org to prevent abuse (e.g. 200/hour per org).
- **SPF/DKIM/DMARC** — enforce on all outbound mail. Reject spoofed inbound.
- **TLS everywhere** — SMTPS (465), IMAPS (993), HTTPS for JMAP/API. Let's Encrypt auto-renewal.
- **Credential isolation** — each mailbox has its own credentials. Django never stores mail passwords — it provisions via the admin API and the user sets their own.
- **Org isolation** — JMAP proxy must verify the authenticated user owns the mailbox they're querying. Never allow cross-org mail access.

---

## 11. Deployment Steps

### Initial Setup (One-time)

1. **Provision Mail VPS** — Hetzner CX22 or equivalent
2. **Set PTR record** — via VPS provider panel → `mail.developeros.pro`
3. **DNS records** — MX, A, SPF, DMARC for `developeros.pro`
4. **Install Docker** — standard Docker + Compose on the mail VPS
5. **Deploy Stalwart** — `docker compose up -d`
6. **Configure Stalwart** — storage backend (PostgreSQL + S3), TLS certs (Let's Encrypt), rate limits
7. **Generate DKIM keys** — via Stalwart admin, publish to DNS
8. **Test** — send/receive with a test account, verify SPF/DKIM/DMARC pass
9. **Warm IP** — start with low volume, gradually increase over 2-4 weeks

### Integration (Development)

1. **Django `mail` app** — models, Stalwart client, API views, JMAP proxy
2. **Auto-provision** — when org is created, create `orgslug.developeros.pro` subdomain + postmaster mailbox
3. **Inbox UI** — SvelteKit JMAP client with the component set above
4. **Admin UI** — domain/mailbox management for org admins
5. **Console UI** — platform-wide mail admin for the console app
6. **DNS verification** — Celery periodic task to check tenant domain records
7. **Quota sync** — Celery task to pull storage usage from Stalwart → update local models

---

## 12. Timeline Estimate

| Phase | Scope | Duration |
|-------|-------|----------|
| **Infra** | VPS, Stalwart, DNS, TLS, test send/receive | 1 day |
| **Phase 1 Backend** | Django models, Stalwart client, provisioning API, JMAP proxy | 3-4 days |
| **Phase 1 Inbox UI** | Message list, reader, compose, folders, search | 5-7 days |
| **Phase 1 Admin** | Domain wizard, mailbox CRUD, quota dashboard | 2-3 days |
| **Testing & Polish** | Deliverability, spam testing, edge cases | 2-3 days |
| **Phase 2** | Groups, signatures, filters, auto-responders | 5-7 days |
| **Phase 3** | Analytics, retention, scheduled send, encryption | 5-7 days |

**MVP (Phase 1): ~2 weeks**

---

## 13. Environment Variables (App VPS)

```env
# Add to .env / docker-compose secrets
STALWART_API_URL=https://mail.developeros.pro:8080/api
STALWART_JMAP_URL=https://mail.developeros.pro/.well-known/jmap
STALWART_ADMIN_USER=admin
STALWART_ADMIN_PASSWORD=<secure_password>
MAIL_DEFAULT_QUOTA=1073741824  # 1GB per mailbox
MAIL_MAX_ATTACHMENT_SIZE=26214400  # 25MB
MAIL_OUTBOUND_RATE_LIMIT=200  # per org per hour
```

---

## 14. Verification Checklist (Pre-Launch)

- [ ] PTR record resolves to `mail.developeros.pro`
- [ ] MX record for `developeros.pro` points to `mail.developeros.pro`
- [ ] SPF passes (`v=spf1 mx ~all`)
- [ ] DKIM signatures verify
- [ ] DMARC policy published
- [ ] TLS certificates valid on all ports (25, 465, 587, 993, 443)
- [ ] Send test to Gmail — lands in inbox, not spam
- [ ] Send test to Outlook — lands in inbox
- [ ] Receive test from external sender
- [ ] Stalwart admin panel accessible
- [ ] REST API provisioning works (create domain, create account)
- [ ] JMAP proxy returns mailbox data through Django
- [ ] IP warm-up plan in place (start < 50 emails/day, ramp over 4 weeks)
