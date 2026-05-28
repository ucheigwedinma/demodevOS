# Domain Glossary

A few terms in this codebase look like they mean one thing but mean another.
This page is the source of truth.

## Organization

**The platform tenant.** A customer company that pays for DeveloperOS — e.g.
"Acme Properties Ltd". An Organization owns users, projects, properties,
documents, and every other piece of data in the system.

- Model: `apps.accounts.Organization`
- Multi-tenancy is enforced by `OrganizationMiddleware`, which injects the
  active org onto each request. All querysets are filtered by org FK.
- Synonyms: org, tenant org, customer, account.

> When SaaS people say "tenant" (as in "multi-tenant architecture"), they
> mean an Organization in this codebase.

## Tenant

**A residential lease holder.** A person (or household) who occupies a unit
under a lease — e.g. the person renting apartment 14B in a finished building.
Tenants do not log into the platform; they are *records* managed by an
Organization's staff.

- App: `apps.tenants`
- Models: `TenantProfile`, `LeaseAgreement`, `OccupancyRecord`,
  `LeaseRenewalRequest`, `TenantComplaint`, etc.
- Frontend route: `/tenants`
- Synonyms: lease holder, occupant, resident.

> When real estate people say "tenant", they mean this. The user-facing UI
> uses this word because it matches industry vocabulary.

## Why the overlap exists

Both meanings of "tenant" are correct in their respective domains:

- SaaS engineering: "tenant" = the customer of a multi-tenant system
- Real estate: "tenant" = the person leasing a property

DeveloperOS is a SaaS *for* real estate, so both worlds collide. The code
resolves the collision by reserving "tenant" for the real estate meaning
and using **Organization** for the SaaS meaning. There is no model named
`Tenant` representing a customer org, and there never should be.

## Platform Operator

**A DeveloperOS staff member.** Someone who runs the platform itself —
provisions customer Organizations, investigates incidents, manages
platform-wide configuration, etc.

- Audience for: `console/` (the SvelteKit admin app) **and** Django `/admin/`.
  These two surfaces serve the same people. `console/` provides a nicer UX
  over a subset of what Django admin does; the rest still happens in
  `/admin/`.
- Authentication: typically `is_staff=True` / `is_superuser=True` Django
  users; not gated by Organization membership.
- Synonyms: platform admin, internal admin, ops, DeveloperOS staff.

> Platform Operators do not belong to any single Organization. They have
> cross-org visibility, which is exactly why their tools live outside the
> per-org `client/` app.

## Organization User

**An employee of a customer Organization.** The actual day-to-day user of
the product — project managers, finance staff, contractors-on-payroll,
property managers, etc.

- Audience for: `client/` (the main SvelteKit app).
- Authentication: a regular `User` scoped to one Organization (or its
  Subsidiaries). All their data is filtered by org FK via
  `OrganizationMiddleware`.
- Per-org admin (managing *their own* org's users / roles / settings) is
  done from `client/` in the `iam` and `settings` route groups, **not** from
  `console/`. Org admins are still Organization Users — they just have
  elevated RBAC roles within their org.

> An Organization Admin is a kind of Organization User. They are not a
> Platform Operator and have no visibility outside their own org.

## Related concepts

| Term | Meaning | Where |
|------|---------|-------|
| User | A person with a login (Organization User unless `is_staff`) | `apps.accounts.User` |
| UserProfile | Extended attributes on a User | `apps.accounts` |
| Subsidiary | A legal sub-entity under an Organization | `apps.settings.Subsidiary` |
| Partner | An external company an Organization works with | `apps.partners` |
| Contractor | A construction firm engaged on a project | `apps.construction` |
| Lead | A potential buyer/renter in the sales pipeline | `apps.crm` |
