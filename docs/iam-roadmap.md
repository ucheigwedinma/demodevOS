# IAM Roadmap

Snapshot: **2026-05-05.** Inventory of the `client/src/routes/iam/` route
tree and what's needed server-side to bring each scaffold to working state.

## Today's state

| Bucket | Count |
|--------|-------|
| WORKING (UI + endpoints both real) | 9 |
| SCAFFOLD (UI exists, no backend yet — intentional roadmap) | 44 |
| WIRED-TO-MISSING (UI calls a non-existent endpoint) | 0 |

The disciplined "no orphans" property is worth preserving — every page
ships only when its endpoint ships. Avoid merging UI for a route that
doesn't yet have a backend.

### Working today (don't break these)

| Route | Backend |
|-------|---------|
| `iam/users/` | `/iam/users/` |
| `iam/users/invite/` | `/iam/users/invitations/` |
| `iam/users/lifecycle/` | `/iam/users/lifecycle/` |
| `iam/roles/` | `/settings/roles/` |
| `iam/roles/permission-matrix/` | `/settings/permission-registry/`, `/settings/roles/{id}/permissions/` |
| `iam/roles/role-assignment/` | `/iam/users/`, `/settings/roles/`, `/iam/users/{id}/` |
| `iam/roles/[id]/permissions/` | `/settings/roles/{id}/permissions/` |
| `iam/service-accounts/` | `/iam/service-accounts/`, `/iam/service-accounts/{id}/keys/` |
| `iam/api-keys/` | `/iam/api-keys/` |
| `iam/auth/mfa/` | `/iam/mfa-settings/` |

## Scaffold inventory and what each needs

Grouped by cluster. Each row gives a sketch of what backend work is
required — model(s), API endpoints, and any cross-cutting infrastructure.
These are *sketches*, not specs; treat them as the starting point for an
ADR before building.

### Cluster 1 — User sub-routes (5 scaffolds)

Extensions to the existing `User`/`UserProfile` model. Lowest dependency
weight; build first to round out the existing user surface.

| Route | Backend sketch |
|-------|----------------|
| `iam/users/profiles` | Likely just a richer UI over existing UserProfile model. May not need new endpoints — could read/write `/iam/users/{id}/profile/`. |
| `iam/users/status` | Status field on User (active/suspended/locked/pending) + history log. New: `/iam/users/{id}/status/` with PATCH. |
| `iam/users/groups` | Group membership UI. Either reuse Django Group or introduce `UserGroup` model with FK to Organization. New: `/iam/user-groups/`. |
| `iam/users/external` | Distinguish external users (contractors, partner staff) from internal employees. Boolean flag on User + filter on `/iam/users/?is_external=true`. |
| `iam/users/linked-employees` | Link User → HR Employee record. New: `/iam/users/{id}/employee-link/`. Cross-app dependency on `apps.hr`. |

### Cluster 2 — API & System Access (3 scaffolds)

| Route | Backend sketch |
|-------|----------------|
| `iam/webhooks` | New `Webhook` model (org-scoped): URL, events, secret, status, last delivery. Background job to deliver + retry. New: `/iam/webhooks/`. Probably backed by Celery for delivery; needs an event registry. |
| `iam/app-tokens` | OAuth2-style application tokens distinct from per-user JWTs. New `Application` + `ApplicationToken` models. Substantial work — consider `django-oauth-toolkit`. |
| `iam/integrations` | Catalogue of third-party connectors (Slack, Notion, Stripe…). Probably a `Connector` model + per-org `ConnectorInstallation`. Each connector is its own integration project; this page is the index. |

### Cluster 3 — Roles sub-routes (4 scaffolds)

All operate on the existing `Role` and `RolePermission` models. Mostly UI
work; backend is largely already in place.

| Route | Backend sketch |
|-------|----------------|
| `iam/roles/create` | Likely just a richer "create role" page than the modal in `iam/roles/`. Backend exists (`POST /settings/roles/`). |
| `iam/roles/module-access` | Toggle entire modules on/off per role. Already implied by the permission registry; new endpoint or filter view. |
| `iam/roles/feature-access` | Feature-level toggles. May need a new `Feature` taxonomy. |
| `iam/roles/data-access-scope` | Row-level scoping (e.g. "this role only sees projects in region X"). Significant — requires per-model scope rules + queryset filtering. Defer until a concrete use-case lands. |

### Cluster 4 — Access Policies (7 scaffolds)

**Highest backend cost in the roadmap.** Each is enforcement at request
time, not just configuration. Requires a policy engine + middleware.

| Route | Backend sketch |
|-------|----------------|
| `iam/access-policies` (parent) | `AccessPolicy` model: name, conditions JSON, action (allow/deny/step-up). |
| `iam/access-policies/conditional` | Conditional access — IF X THEN Y. The policy engine itself. |
| `iam/access-policies/ip-restrictions` | Per-org IP allowlist. Cheap if just config, expensive if it has to integrate with the policy engine. |
| `iam/access-policies/device-restrictions` | Device fingerprinting + binding. Needs a frontend SDK to capture device fingerprints + a `Device` model. |
| `iam/access-policies/location-restrictions` | Geo-IP lookup at login + per-policy enforcement. |
| `iam/access-policies/time-based` | Schedule-based access (e.g. "no logins outside 9–6"). Cheap; cron-style rules. |
| `iam/access-policies/session-duration` | Per-role/per-policy max session length. Touches JWT issue/refresh logic. |

**Recommendation:** treat this whole cluster as one project. Build the
policy engine first as a request-time middleware, then layer the UIs on
top. Don't build the UIs piecemeal against an absent engine.

### Cluster 5 — Access Requests (5 scaffolds)

Just-in-time access workflow. New domain — needs its own model set.

| Route | Backend sketch |
|-------|----------------|
| `iam/access-requests` (parent) | `AccessRequest` model: requester, target (role or resource), reason, status, expires. New: `/iam/access-requests/`. |
| `iam/access-requests/approvals` | Approval queue UI. Reuses existing `apps.workflows` for approval routing. |
| `iam/access-requests/temporary` | Temporary role grants with auto-expiry. `RoleAssignment` needs a `valid_until` field; needs a Celery sweeper to revoke expired ones. |
| `iam/access-requests/expiry` | Just a filtered view of temporary assignments approaching expiry. UI-only once `valid_until` exists. |
| `iam/access-requests/elevation` | Privilege elevation (sudo). User asks for a stronger role for N minutes. Specialised AccessRequest. |

**Recommendation:** build `AccessRequest` + `temporary` + `expiry` as a
unit; `approvals` is a queue UI on top; `elevation` is a special case.

### Cluster 6 — Audit (Login Activity sub-routes — now in `settings/audit/`)

These routes were moved out of `iam/` to `settings/audit/` on 2026-05-05.
Listing them here for completeness.

`settings/audit/login-activity`, `settings/audit/access-logs`,
`settings/audit/permission-changes`, `settings/audit/role-changes`,
`settings/audit/failed-logins`, `settings/audit/privilege-escalations`,
`settings/audit/security-alerts` — 7 scaffolds.

| Backend sketch |
|----------------|
| There's already an `apps.notifications` event feed and a generic audit log writer somewhere in the codebase (used by various models for change tracking). The work here is largely **wiring**: emit structured audit events at the right SDK seams (login success/failure, permission grant/revoke, role assignment, sudo) and surface them through filtered list endpoints. |
| Suggested model: `AuditEvent(actor, organization, kind, target, payload, ip, user_agent, occurred_at)` with `kind` as an indexed string. Each scaffold is then a filter on `kind` + a domain-specific UI. |

### Cluster 7 — Authentication & Security (5 scaffolds, MFA already built)

| Route | Backend sketch |
|-------|----------------|
| `iam/auth` (parent) | Password policies — min length, expiry, history. Settings on `Organization` or a new `PasswordPolicy` model. |
| `iam/auth/sso` | Generic SSO gateway page (probably overlaps with federation/*). |
| `iam/auth/oauth-saml` | Custom OAuth/SAML endpoint for non-federated SSO. May be unneeded if federation/* handles all the IDPs. |
| `iam/auth/login-methods` | Per-org enable/disable of login methods (password, passkey, OAuth, SAML, biometric). Depends on each method existing first. |
| `iam/auth/biometric` | Already partially supported via WebAuthn (passkeys). May just be a UX page over existing passkey enrolment. |
| `iam/auth/sessions` | Active session list + revoke. Needs persistent session storage (currently sessions live in JWT only). New `UserSession` model + revocation list. |

### Cluster 8 — Identity Federation (5 scaffolds)

**Equivalent backend cost to access policies.** Each row is a real auth
backend integration with a third-party identity provider.

| Route | Backend sketch |
|-------|----------------|
| `iam/federation/active-directory` | NTLM/Kerberos or LDAP-over-AD. Likely subsumes `ldap` row. |
| `iam/federation/ldap` | `django-auth-ldap` integration; per-org bind config. |
| `iam/federation/azure-ad` | OIDC via Azure AD. `django-allauth` or custom. |
| `iam/federation/google-workspace` | OIDC via Google. `django-allauth` already does this — Google OAuth is partly wired (mentioned in earlier deploy refactor commits). Could be near-done. |
| `iam/federation/external-idp` | Generic OIDC/SAML for any IDP not specifically supported. |

**Recommendation:** start with Google Workspace (already partly done),
then Azure AD as the next-most-asked enterprise IDP. LDAP/AD/external-IdP
are heavier and lower-frequency asks; defer until a customer requires
them.

### Cluster 9 — Compliance & Monitoring (5 scaffolds)

Periodic-review tooling. Most of these require an audit event stream
(see Cluster 6) as input.

| Route | Backend sketch |
|-------|----------------|
| `iam/compliance/access-reviews` | Quarterly review workflow. New `AccessReviewCampaign` model + per-user review state. Reuses workflow engine. |
| `iam/compliance/role-certification` | Manager attests "yes, this user should still have this role." Subset of access reviews. |
| `iam/compliance/dormant-accounts` | Filter view on User by `last_login` > N days. UI-only once cluster 6's audit feed exists. |
| `iam/compliance/privilege-risk` | Risk scoring per user/role based on permission breadth + recent activity. Largely a computed view — `PrivilegeRiskScore` materialised in a periodic Celery job. |
| `iam/compliance/reports` | Export-oriented. Reuses the reporting engine in `apps.settings.report_*`. |

## Suggested build order

A phasing that keeps each phase shippable and each phase's prerequisites
already in place:

1. **Cluster 1** (user sub-routes) — extends what's already built.
2. **Cluster 3** (roles sub-routes, except data-access-scope) — UI on existing backend.
3. **Cluster 6** (audit event stream) — unblocks compliance + several auth sub-routes.
4. **Cluster 5** (access requests + temporary access) — depends on workflow engine, already in place.
5. **Cluster 7** (auth methods minus SSO) — `auth`, `login-methods`, `biometric`, `sessions`.
6. **Cluster 8** (federation, starting with Google Workspace).
7. **Cluster 4** (access policies) — biggest backend cost; build the policy engine here.
8. **Cluster 9** (compliance) — reads from the audit feed and policy engine.
9. **Cluster 2** (webhooks, app tokens, integrations catalogue) — mostly new domain.
10. **Cluster 3 — `data-access-scope`** — defer until a real use-case lands.

## Conventions to keep

- **Don't ship orphans.** Frontend pages that call endpoints that don't
  exist accumulate as silent debt. Today this property is preserved
  (zero orphans across 53 routes); keep it that way.
- **Every working form needs a Dev Fill button** (per the project's
  existing rule). Sample data lives in `const SAMPLES` arrays at the top
  of the page; `isDev` gate is `["localhost", "127.0.0.1"].includes(...)`.
- **All new endpoints honour the multi-tenant boundary.** Use
  `_scope_queryset_for_request` in `get_queryset` — superusers see all,
  org users see their own, profile-less users see `.none()` (not a
  silent NULL filter).
- **Audit-emitting actions write a structured event** once Cluster 6
  lands. Until then, pin a TODO at the call site so the wiring isn't
  forgotten.
