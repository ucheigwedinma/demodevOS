# DeveloperOS — context for AI assistants

DeveloperOS is a multi-tenant SaaS platform for real estate developers.
Backend: Django 5.2 + DRF + PostgreSQL 16 + Redis + Celery.
Frontend: Svelte 5 (runes) + SvelteKit (adapter-static SPA), Tailwind 4.

Two SvelteKit apps with **different audiences** — do not confuse them:

- **`client/`** — the product itself, used by Organization users (employees of
  the customer companies that buy DeveloperOS). Per-org admin features
  (managing the org's own users, roles, settings) live here. Within `client/`:
  - `iam/` owns identity, access, roles, authentication, and federation
  - `settings/` owns operational/security configuration, including audit
    & activity logs (audit was previously split across iam/ and settings/;
    consolidated to settings/ on 2026-05-05)
- **`console/`** — internal tool for **Platform Operators** (the DeveloperOS
  team). Same audience as Django `/admin/`; console is a richer UX over
  the same data, with additional platform-wide capabilities Django admin
  can't comfortably express. Not a per-organization admin panel.

If you find yourself adding org-admin features to `console/` or platform-ops
features to `client/`, stop — you almost certainly want the other app.

### Platform Operator identity

Platform Operators are **`is_superuser=True`** Django users (not merely
`is_staff`). Backend cross-org visibility is gated on `is_superuser` — see
`apps.settings.views._scope_queryset_for_request`. Two consequences:

- `is_staff` alone does *not* grant cross-org access at the API layer.
  An `is_staff`-only user operating from `console/` will see only their own
  org via the API, even if the UI implies otherwise.
- `is_superuser=True` bypasses Django's RBAC permission checks entirely.
  Granting it should be treated like granting root.

## Vocabulary trap: "tenant"

The word **tenant** is overloaded in this codebase. Read carefully:

- **Organization** = the platform tenant (the customer org paying for DeveloperOS).
  Lives in `apps.accounts.Organization`. Multi-tenancy is enforced by
  `OrganizationMiddleware` which filters all data by org FK. **This is what
  SaaS people mean by "tenant".**

- **Tenant** = a residential lease holder (the person renting a unit in a
  finished building). Lives in `apps.tenants`. Models: `TenantProfile`,
  `LeaseAgreement`, etc. **This is what real-estate people mean by "tenant".**

When you see `apps.tenants`, it is **never** about SaaS multi-tenancy.
When you need the customer-org concept, use `Organization`.

Full domain glossary: [`docs/glossary.md`](docs/glossary.md).

## Branch & deploy

- Local work always happens on `staging`. Never leave the repo on `main`.
- Flow: work on `staging` → test → merge `staging` into `main` for production.
- Staging deploy: VPS `158.220.99.54` (SSH alias `staging`), path
  `/opt/developerOS/`, compose file `docker-compose.staging.yml`. CI
  workflow `.github/workflows/deploy-staging.yml` rsyncs source to
  that path, then SSHes in to `docker compose up -d --build` the
  backend stack and rsyncs static frontend builds to
  `/var/www/developeros/{client,console}/` for nginx to serve.

## Brand mark

Render the brand as `developer` (regular weight, **black**) + `OS` (bold, **grey**).
Never plain-text "developerOS".

```html
<span class="font-normal text-neutral-900">developer</span><span class="font-bold text-neutral-400">OS</span>
```

On dark backgrounds use `text-white` for `developer` and keep `text-neutral-400`
for `OS`.

## Style conventions

- **Font:** Raleway, everywhere.
- **Palette:** monochrome by default. Add colour accents only when explicitly asked.
- **Forms:** every form needs a Dev Fill button for localhost testing.
- **Server processes:** never `pkill` or restart a running dev server / port
  without asking the user first.
